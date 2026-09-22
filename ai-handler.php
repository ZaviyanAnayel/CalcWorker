<?php
/**
 * CalcWorker AI — Server-Side API Gateway & Domain Intelligence Engine
 * Supports xAI Grok and OpenAI API, with built-in intelligent fallback.
 * Configured for cPanel / LiteSpeed PHP environments.
 */

declare(strict_types=1);

header('Content-Type: application/json; charset=utf-8');
header('X-Content-Type-Options: nosniff');
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: POST, OPTIONS');
header('Access-Control-Allow-Headers: Content-Type');

if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
    http_response_code(200);
    exit;
}

if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    http_response_code(405);
    echo json_encode(['error' => 'Method Not Allowed']);
    exit;
}

// 1. Parse & Sanitize Input
$rawInput = file_get_contents('php://input');
$data = json_decode($rawInput, true);

if (!is_array($data) || empty(trim((string)($data['prompt'] ?? '')))) {
    http_response_code(400);
    echo json_encode(['error' => 'Invalid prompt']);
    exit;
}

$prompt = trim((string)$data['prompt']);
if (mb_strlen($prompt) > 800) {
    $prompt = mb_substr($prompt, 0, 800);
}

$history = is_array($data['history'] ?? null) ? array_slice($data['history'], -6) : [];

// 2. Intelligent Server-Side Response Engine (Active if no external API key)
$apiKey = getenv('GROK_API_KEY') ?: getenv('OPENAI_API_KEY') ?: '';

function getSmartFallback(string $q): string {
    $lower = mb_strtolower($q);

    if (str_contains($lower, 'owner') || str_contains($lower, 'zaviyan') || str_contains($lower, 'founder') || str_contains($lower, 'who made') || str_contains($lower, 'who created') || str_contains($lower, 'kisne')) {
        return "CalcWorker was founded, built, and is operated by Zaviyan (Zaviyan LLC). Zaviyan designed CalcWorker to provide 100% private, client-side, zero-latency financial and computational tools for US freelancers, homeowners, creators, and business owners. Contact: business@zaviyanllc.com";
    }

    if (str_contains($lower, 'email') || str_contains($lower, 'contact') || str_contains($lower, 'support') || str_contains($lower, 'rabta')) {
        return "You can reach Zaviyan and the CalcWorker team directly at official email: business@zaviyanllc.com for inquiries, partnerships, feedback, and custom tool requests.";
    }

    if (str_contains($lower, 'new tool') || str_contains($lower, 'new calculator') || str_contains($lower, 'naye tool') || str_contains($lower, 'latest') || str_contains($lower, 'recent') || str_contains($lower, 'what is new') || str_contains($lower, "what's new") || $lower === 'new') {
        return "🎉 6 Brand-New Precision Calculators have been added to CalcWorker (2026):\n\n" .
            "1. Mortgage Refinance Break-Even: Calculate exact months to recoup closing costs and net lifetime savings (/tools/mortgage-refinance-calculator.html)\n" .
            "2. State Tax Relocation Calculator: Compare take-home pay boost across all 50 US States + DC before moving (/tools/state-tax-relocation-calculator.html)\n" .
            "3. CD Ladder Yield Calculator: Optimize Certificate of Deposit multi-year rolling yields (/tools/cd-ladder-calculator.html)\n" .
            "4. Life Insurance Needs (DIME Formula): Determine exact term life coverage needed for debt, mortgage, and kids' college (/tools/life-insurance-calculator.html)\n" .
            "5. Substack Newsletter Revenue: Project creator MRR and ARR after 10% Substack and Stripe fees (/tools/substack-calculator.html)\n" .
            "6. Flooring & Tile Square Footage: Calculate square feet, 10% cut waste, boxes, and project costs (/tools/flooring-calculator.html)\n\n" .
            "All 6 new tools are live in the sidebar, search bar, and home dashboard!";
    }

    if (str_contains($lower, 'online') || str_contains($lower, 'offline') || str_contains($lower, 'connected') || str_contains($lower, 'internet')) {
        return "Yes, you are 100% online and connected! CalcWorker runs live in real time and also features full offline caching so you never lose access. All 102 calculators and mathematical tools are active. What calculation can I help you with?";
    }

    if ($lower === 'hi' || $lower === 'hello' || $lower === 'hey' || str_contains($lower, 'salam') || str_contains($lower, 'kaise') || str_contains($lower, 'haal')) {
        return "Hello! I am CalcWorker AI, built by Zaviyan (Zaviyan LLC). I can help you solve complex math, calculate 1099 taxes, 50-state relocation taxes, mortgage refinance break-even, TikTok creator earnings, CD ladders, and more across all 102 tools. What are you calculating today?";
    }

    if (str_contains($lower, 'who are you') || str_contains($lower, 'what can you do') || str_contains($lower, 'calcworker') || str_contains($lower, 'help')) {
        return "I am CalcWorker AI, trained on over 102 calculators covering Real Estate, US Taxation, Personal Finance, E-Commerce, Creator Economics, and Fitness. I provide exact mathematical formulas, variable breakdowns, step-by-step methods, and links to our instant calculation tools.";
    }

    if (str_contains($lower, 'amazon') || str_contains($lower, 'fba')) {
        return "For Amazon FBA, net profit = List Price - Landed Cost - Referral Fee (usually 15%) - FBA Fulfillment Fee - Storage Fees. To minimize fees, ensure package dimensions stay within Standard Size tiers. You can use our <a href='/tools/amazon-fba-calculator.html'>Amazon FBA Calculator</a> for an exact 2026 fee breakdown!";
    }

    if (str_contains($lower, 'tiktok') || str_contains($lower, 'coin') || str_contains($lower, 'diamond')) {
        return "On TikTok: 100 coins cost ~$1.05 USD on desktop web (recharging on web avoids Apple/Google 30% fees). When gifts are sent to creators, 2 diamonds = 1 coin value, and TikTok takes a 50% revenue cut, making 1 diamond worth ~$0.005 USD upon cashout. Try our <a href='/tools/tiktok-coins-calculator.html'>TikTok Coin Calculator</a>!";
    }

    if (str_contains($lower, 'tax') || str_contains($lower, '1099') || str_contains($lower, 'irs')) {
        return "US 1099 self-employment tax is 15.3% (12.4% Social Security + 2.9% Medicare) applied to 92.35% of your net Schedule C business profit after legitimate deductions. Check out our <a href='/tools/freelance-tax-calculator.html'>1099 Tax Calculator</a> and <a href='/tools/federal-tax-bracket-calculator.html'>Federal Tax Bracket Calculator</a>!";
    }

    if (str_contains($lower, 'mortgage') || str_contains($lower, 'loan') || str_contains($lower, 'piti') || str_contains($lower, 'interest')) {
        return "Mortgage payments (PITI) combine Principal & Interest amortized over your term, plus property taxes, insurance, and PMI (if down payment is under 20%). Use our <a href='/tools/mortgage-calculator.html'>Mortgage Calculator</a> to calculate monthly payments and amortization schedules!";
    }

    if (str_contains($lower, 'gpa') || str_contains($lower, 'grade')) {
        return "Collegiate GPA is calculated as: Total Quality Points (Grade Point × Credit Hours for each course) divided by Total Credit Hours Attempted. A = 4.0, B = 3.0, C = 2.0, D = 1.0, F = 0.0. Calculate your semester or cumulative standing with our <a href='/tools/gpa-calculator.html'>GPA Calculator</a>!";
    }

    if (str_contains($lower, 'refinance') || str_contains($lower, 'refi')) {
        return "Mortgage refinance break-even is calculated as: Closing Costs divided by Monthly Payment Savings. Use our <a href='/tools/mortgage-refinance-calculator.html'>Mortgage Refinance Break-Even Calculator</a> to find out how many months until you recover fees and how much lifetime interest you save!";
    }

    if (str_contains($lower, 'relocat') || str_contains($lower, 'moving') || str_contains($lower, 'texas') || str_contains($lower, 'florida')) {
        return "Moving across US states? Zero-tax states like Texas, Florida, and Nevada have 0% individual income tax compared to California (up to 13.3%) or New York. Use our <a href='/tools/state-tax-relocation-calculator.html'>State Tax Relocation Calculator</a> to calculate your exact take-home pay boost!";
    }

    if (str_contains($lower, 'life insurance') || str_contains($lower, 'dime')) {
        return "The DIME method calculates life insurance coverage: Debt + Income replacement (10-12x salary) + Mortgage payoff + Education fund - Existing savings. Use our <a href='/tools/life-insurance-calculator.html'>Life Insurance Needs Calculator</a> to calculate your recommended policy!";
    }

    if (str_contains($lower, 'cd ladder') || str_contains($lower, 'certificate of deposit')) {
        return "A CD ladder divides your savings into staggered CDs (e.g. 1 to 5 years) to lock in top APY yields while giving you cash liquidity every 12 months without penalty. Try our <a href='/tools/cd-ladder-calculator.html'>CD Ladder Yield Calculator</a>!";
    }

    if (str_contains($lower, 'substack') || str_contains($lower, 'newsletter')) {
        return "Substack takes a 10% platform fee and Stripe charges ~2.9% + 30¢, leaving creators with ~85% net take-home earnings. With a 3% conversion rate on 10,000 free readers, you can earn over $20,000/yr. Calculate your newsletter earnings with our <a href='/tools/substack-calculator.html'>Substack Revenue Calculator</a>!";
    }

    if (str_contains($lower, 'flooring') || str_contains($lower, 'tile') || str_contains($lower, 'lvp')) {
        return "To calculate flooring materials: Area = Length × Width + Closets. Always add a 10% waste factor for cuts (15% for diagonal), then divide by box coverage and round up. Check your project costs with our <a href='/tools/flooring-calculator.html'>Flooring & Tile Cost Calculator</a>!";
    }

    return "I can help you solve that calculation! CalcWorker features 102 precision calculators across Real Estate, Taxes, Investments, Creator Economy, and Health. Tell me the numbers or variables you're working with, or select a calculator from the left sidebar!";
}

// 3. If no external API key, return smart internal response
if (empty($apiKey)) {
    echo json_encode([
        'reply' => getSmartFallback($prompt)
    ]);
    exit;
}

// 4. Dispatch External API Request (xAI Grok or OpenAI)
$systemPrompt = "You are CalcWorker AI, an elite mathematical, financial, and creator-economy calculator assistant for CalcWorker.com. "
    . "Always provide clear, humanized, step-by-step mathematical solutions and cite relevant US standards (IRS, CFPB, BLS, CDC). "
    . "Break down complicated formulas into simple intuitive steps. Recommend relevant CalcWorker calculators when helpful.";

$messages = [
    ['role' => 'system', 'content' => $systemPrompt]
];

foreach ($history as $h) {
    if (isset($h['role'], $h['content']) && is_string($h['role']) && is_string($h['content'])) {
        $role = in_array($h['role'], ['user', 'assistant']) ? $h['role'] : 'user';
        $messages[] = ['role' => $role, 'content' => mb_substr($h['content'], 0, 800)];
    }
}

$messages[] = ['role' => 'user', 'content' => $prompt];

$apiUrl = 'https://api.x.ai/v1/chat/completions';
$model = 'grok-beta';

if (str_starts_with($apiKey, 'sk-')) {
    $apiUrl = 'https://api.openai.com/v1/chat/completions';
    $model = 'gpt-4o-mini';
}

$payload = json_encode([
    'model' => $model,
    'messages' => $messages,
    'temperature' => 0.4,
    'max_tokens' => 600
]);

$ch = curl_init($apiUrl);
curl_setopt_array($ch, [
    CURLOPT_RETURNTRANSFER => true,
    CURLOPT_POST => true,
    CURLOPT_POSTFIELDS => $payload,
    CURLOPT_HTTPHEADER => [
        'Content-Type: application/json',
        'Authorization: Bearer ' . $apiKey
    ],
    CURLOPT_TIMEOUT => 15,
    CURLOPT_SSL_VERIFYPEER => true
]);

$response = curl_exec($ch);
$httpCode = curl_getinfo($ch, CURLINFO_HTTP_CODE);
curl_close($ch);

if ($httpCode === 200 && $response) {
    $resData = json_decode($response, true);
    $botReply = $resData['choices'][0]['message']['content'] ?? null;
    if ($botReply) {
        echo json_encode(['reply' => $botReply]);
        exit;
    }
}

// Fallback to internal smart responder if external API fails
echo json_encode([
    'reply' => getSmartFallback($prompt)
]);
