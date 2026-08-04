using System.Text;

var baseUrl = Environment.GetEnvironmentVariable("WELLMANIFEST_URL") ?? "http://localhost:8080";
var json = """
{"source":"status:\n  value: SUCCEEDED\n  errors: []\n","source_dialect":"yaml","target_dialect":"json","projection":"data"}
""";
using var client = new HttpClient();
using var response = await client.PostAsync(
    baseUrl + "/v1/convert",
    new StringContent(json, Encoding.UTF8, "application/json"));
var body = await response.Content.ReadAsStringAsync();
response.EnsureSuccessStatusCode();
Console.WriteLine(body);
