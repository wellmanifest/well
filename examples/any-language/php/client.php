<?php
$base = getenv('WELLMANIFEST_URL') ?: 'http://localhost:8080';
$payload = json_encode([
  'source' => "status:\n  value: SUCCEEDED\n  errors: []\n",
  'source_dialect' => 'yaml',
  'target_dialect' => 'json',
  'projection' => 'data',
]);
$curl = curl_init($base . '/v1/convert');
curl_setopt_array($curl, [
  CURLOPT_POST => true,
  CURLOPT_HTTPHEADER => ['content-type: application/json'],
  CURLOPT_POSTFIELDS => $payload,
  CURLOPT_RETURNTRANSFER => true,
]);
$result = curl_exec($curl);
if ($result === false || curl_getinfo($curl, CURLINFO_HTTP_CODE) >= 300) {
  throw new RuntimeException(curl_error($curl) ?: (string)$result);
}
echo $result, PHP_EOL;
curl_close($curl);
