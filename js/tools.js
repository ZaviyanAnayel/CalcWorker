/* CalcWorker Tools Engine — window.cwTools
 *
 * Shared calculation library for tool pages. Defines pure computation
 * functions consumed by inline page scripts (break-even, compound-interest,
 * debt-payoff, gig-profit, hourly-rate, retirement-401k, solar-roi,
 * student-loan, tax-withholding).
 *
 * All figures use 2026 IRS parameters (Rev. Proc. 2025-32):
 *   standard deductions single $16,100 / MFJ $32,200 / HoH $24,150
 *   Social Security wage base $184,500
 */
(function () {
  'use strict';

  function num(v, d) {
    var n = parseFloat(v);
    return isNaN(n) ? (d || 0) : n;
  }

  /* ---------- 2026 federal tax tables ---------- */
  var STD_DED_2026 = { single: 16100, married: 32200, hoh: 24150, marriedSep: 16100 };
  // [upper bound, rate]
  var BRACKETS_2026 = {
    single:    [[12400, .10], [50400, .12], [105700, .22], [201775, .24], [256225, .32], [640600, .35], [Infinity, .37]],
    married:   [[24800, .10], [100800, .12], [211400, .22], [403550, .24], [512450, .32], [768700, .35], [Infinity, .37]],
    hoh:       [[17700, .10], [67450, .12], [105700, .22], [201750, .24], [256200, .32], [640600, .35], [Infinity, .37]],
    marriedSep:[[12400, .10], [50400, .12], [105700, .22], [201775, .24], [256225, .32], [384350, .35], [Infinity, .37]]
  };
  var SS_WAGE_BASE_2026 = 184500;

  function federalTax(taxable, status) {
    var br = BRACKETS_2026[status] || BRACKETS_2026.single;
    var tax = 0, prev = 0;
    for (var i = 0; i < br.length; i++) {
      if (taxable > prev) {
        tax += (Math.min(taxable, br[i][0]) - prev) * br[i][1];
        prev = br[i][0];
      } else break;
    }
    return tax;
  }

  /* State flat/average rates matching the option labels on tax-withholding */
  var STATE_RATES = { TX: 0, FL: 0, WA: 0, standard: 0.045, PA: 0.0307, NC: 0.0475, CA: 0.065, NY: 0.065 };

  var cwTools = {

    /* Break-even: contribution margin math */
    calcBreakEven: function (p) {
      var fixed = num(p.fixedCosts), vc = num(p.variableCost),
          price = num(p.unitPrice), target = num(p.targetProfit);
      var cm = price - vc;
      var cmRatio = price > 0 ? (cm / price) * 100 : 0;
      var beUnits = cm > 0 ? fixed / cm : 0;
      var targetUnits = cm > 0 ? (fixed + target) / cm : 0;
      return {
        breakEvenUnits: Math.ceil(beUnits),
        breakEvenRevenue: beUnits * price,
        contributionMargin: cm,
        contributionMarginRatio: Math.round(cmRatio * 10) / 10,
        targetUnits: Math.ceil(targetUnits),
        targetRevenue: targetUnits * price
      };
    },

    /* Compound interest with monthly deposits, yearly schedule */
    calcCompoundInterest: function (p) {
      var principal = num(p.principal), dep = num(p.monthlyDeposit),
          apr = num(p.annualRate), years = Math.max(0, Math.round(num(p.years))),
          r = apr / 100 / 12, n = years * 12, bal = principal;
      var schedule = [], totalDep = principal, prevBal = principal;
      for (var y = 1; y <= years; y++) {
        var yrDep = 0, yrInt = 0;
        for (var m = 0; m < 12; m++) {
          var interest = bal * r;
          bal += interest + dep;
          yrInt += interest; yrDep += dep;
        }
        totalDep += yrDep;
        schedule.push({ year: y, deposits: Math.round(totalDep), interest: Math.round(bal - totalDep), balance: Math.round(bal) });
        prevBal = bal;
      }
      var fv = years === 0 ? principal : bal;
      return {
        futureValue: Math.round(fv),
        totalInterest: Math.round(fv - totalDep),
        totalDeposits: Math.round(totalDep),
        schedule: schedule
      };
    },

    /* Debt payoff: snowball vs avalanche simulation */
    calcDebtPayoff: function (debts, extraMonthly) {
      function simulate(order) {
        var ds = order.map(function (d) {
          return { balance: num(d.balance), apr: num(d.apr), min: num(d.minPayment) };
        });
        var budget = ds.reduce(function (s, d) { return s + d.min; }, 0) + num(extraMonthly);
        var months = 0, interest = 0, guard = 0;
        while (ds.some(function (d) { return d.balance > 0.005; }) && guard < 1200) {
          guard++;
          var totalMin = 0;
          ds.forEach(function (d) {
            if (d.balance <= 0.005) return;
            var i = d.balance * (d.apr / 100 / 12);
            interest += i; d.balance += i;
            var pay = Math.min(d.min, d.balance);
            d.balance -= pay; totalMin += pay;
          });
          var extra = budget - totalMin;
          for (var k = 0; k < ds.length && extra > 0.005; k++) {
            var t = ds[k];
            if (t.balance <= 0.005) continue;
            var p = Math.min(extra, t.balance);
            t.balance -= p; extra -= p;
          }
          months++;
          if (budget <= ds.reduce(function (s, d) { return s + d.balance * (d.apr / 100 / 12); }, 0)) break; // never-ending
        }
        return { months: months, interest: interest };
      }
      var snow = simulate(debts.slice().sort(function (a, b) { return a.balance - b.balance; }));
      var ava = simulate(debts.slice().sort(function (a, b) { return b.apr - a.apr; }));
      return {
        snowballMonths: snow.months,
        snowballInterest: Math.round(snow.interest),
        avalancheMonths: ava.months,
        avalancheInterest: Math.round(ava.interest),
        interestSavedByAvalanche: Math.max(0, Math.round(snow.interest - ava.interest))
      };
    },

    /* Gig worker profit: fuel + maintenance vs IRS mileage deduction */
    calcGigProfit: function (p) {
      var gross = num(p.grossWeekly), miles = num(p.milesWeekly), hrs = num(p.hoursWeekly) || 1,
          gas = num(p.gasPrice), mpg = num(p.mpg) || 1, maint = num(p.maintPerMile);
      var IRS_MILE_2026 = 0.725;
      var gasCost = miles / mpg * gas;
      var maintCost = miles * maint;
      var net = gross - gasCost - maintCost;
      var irsDed = miles * IRS_MILE_2026;
      return {
        netHourlyActual: net / hrs,
        grossHourly: gross / hrs,
        netWeekly: net,
        annualNet: net * 52,
        irsDeductionWeekly: irsDed,
        gasCostWeekly: gasCost,
        maintCostWeekly: maintCost,
        taxableIncomeIRS: Math.max(0, gross - irsDed)
      };
    },

    /* Freelancer hourly rate from desired net */
    calcHourlyRate: function (p) {
      var desired = num(p.desiredNet), exp = num(p.expenses),
          hrsWk = num(p.billableHrsPerWk) || 1, wks = num(p.weeksWorked) || 1,
          taxR = num(p.taxRate) / 100, buffer = num(p.profitBuffer) / 100;
      var billable = hrsWk * wks;
      var netNeeded = (desired + exp) * (1 + buffer);
      var gross = taxR >= 1 ? netNeeded : netNeeded / (1 - taxR);
      var hourly = billable > 0 ? gross / billable : 0;
      return {
        hourlyRate: Math.round(hourly * 100) / 100,
        totalBillableHours: billable,
        dayRate: hourly * 8,
        weeklyRate: hourly * hrsWk,
        annualGrossTarget: gross,
        monthlyGross: gross / 12,
        totalTaxesEstimated: gross * taxR
      };
    },

    /* 401(k) retirement projection with employer match */
    calcRetirement: function (p) {
      var years = Math.max(0, Math.round(num(p.retirementAge) - num(p.currentAge)));
      var salary = num(p.salary), contrib = num(p.contribPct) / 100,
          matchPct = num(p.matchPct) / 100, matchUpTo = num(p.matchUpTo) / 100,
          r = num(p.annualReturn) / 100 / 12, bal = num(p.currentSavings);
      var empAnnual = salary * contrib;
      var empyrAnnual = Math.min(empAnnual * matchPct, salary * matchUpTo);
      var monthly = (empAnnual + empyrAnnual) / 12;
      for (var m = 0; m < years * 12; m++) bal = bal * (1 + r) + monthly;
      var totalContrib = (empAnnual + empyrAnnual) * years;
      return {
        totalNestEgg: Math.round(bal),
        safeMonthlyIncome: Math.round(bal * 0.04 / 12),
        totalEmployeeContributions: Math.round(empAnnual * years),
        totalEmployerMatch: Math.round(empyrAnnual * years),
        totalInterestEarned: Math.round(bal - num(p.currentSavings) - totalContrib),
        yearsToRetire: years
      };
    },

    /* Solar ROI: 30% federal ITC (2026), 25-yr horizon */
    calcSolarROI: function (p) {
      var bill = num(p.monthlyBill), tariff = num(p.tariffRate),
          kw = num(p.systemSizeKW), sun = num(p.sunHours);
      var COST_PER_WATT = 2.75, ITC_2026 = 0.30;
      var annualKwh = kw * sun * 365;
      var annualSavings = Math.min(annualKwh * tariff, bill * 12);
      var grossCost = kw * 1000 * COST_PER_WATT;
      var credit = grossCost * ITC_2026;
      var netCost = grossCost - credit;
      var payback = annualSavings > 0 ? netCost / annualSavings : 0;
      var net25 = annualSavings * 25 - netCost;
      return {
        net25YrSavings: Math.round(net25),
        paybackYears: Math.round(payback * 10) / 10,
        federalTaxCredit: Math.round(credit),
        netCost: Math.round(netCost),
        annualKwh: Math.round(annualKwh),
        annualSavings: Math.round(annualSavings),
        roiPercent: netCost > 0 ? Math.round(net25 / netCost * 100) : 0
      };
    },

    /* Student loan: standard 10-yr vs extra-payment acceleration */
    calcStudentLoan: function (p) {
      var bal = num(p.balance), apr = num(p.apr) / 100 / 12,
          extra = num(p.extraMonthly), fam = Math.max(1, Math.round(num(p.familySize) || 1));
      // 2026 HHS poverty guidelines (approx): $16,100 + $5,700 per additional member
      var poverty = 16100 + (fam - 1) * 5700;
      var n = 120, stdMonthly = 0, stdInterest = 0;
      if (bal > 0) {
        stdMonthly = apr > 0 ? bal * (apr * Math.pow(1 + apr, n)) / (Math.pow(1 + apr, n) - 1) : bal / n;
        stdInterest = stdMonthly * n - bal;
      }
      var b = bal, months = 0, intPaid = 0, pay = stdMonthly + extra;
      while (b > 0.005 && months < 1200 && pay > 0) {
        var i = b * apr; intPaid += i; b += i;
        b -= Math.min(pay, b); months++;
        if (pay <= b * apr) break;
      }
      return {
        stdMonthly: Math.round(stdMonthly * 100) / 100,
        stdTotalInterest: Math.round(stdInterest),
        saveMonthly: Math.round(extra * 100) / 100,
        accMonths: months,
        interestSavedWithExtra: Math.max(0, Math.round(stdInterest - intPaid)),
        povertyThreshold: poverty
      };
    },

    /* Paycheck tax withholding (2026 IRS figures) */
    calcTaxWithholding: function (p) {
      var gross = num(p.annualGross), status = p.filingStatus || 'single',
          preTax = num(p.preTaxDeductions);
      var stdDed = STD_DED_2026[status] || STD_DED_2026.single;
      var taxable = Math.max(0, gross - preTax - stdDed);
      var fed = federalTax(taxable, status);
      var ss = Math.min(gross, SS_WAGE_BASE_2026) * 0.062;
      var med = gross * 0.0145;
      var addlLimit = status === 'married' ? 250000 : 200000;
      var addl = Math.max(0, gross - addlLimit) * 0.009;
      var fica = ss + med + addl;
      var stateRate = STATE_RATES[p.state] !== undefined ? STATE_RATES[p.state] : STATE_RATES.standard;
      var state = Math.max(0, gross - preTax) * stateRate;
      var total = fed + fica + state;
      var net = gross - total;
      return {
        netBiWeekly: Math.round(net / 26),
        netMonthly: Math.round(net / 12),
        netPayAnnual: Math.round(net),
        effectiveRate: gross > 0 ? Math.round(total / gross * 1000) / 10 : 0,
        fedTax: Math.round(fed),
        ficaTax: Math.round(fica),
        stateTax: Math.round(state),
        totalTaxes: Math.round(total)
      };
    }
  };

  window.cwTools = cwTools;
})();
