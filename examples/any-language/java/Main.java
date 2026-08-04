import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;

public final class Main {
  public static void main(String[] args) throws Exception {
    String base = System.getenv().getOrDefault("WELLMANIFEST_URL", "http://localhost:8080");
    String json = """
      {"source":"status:\\n  value: SUCCEEDED\\n  errors: []\\n",\
       "source_dialect":"yaml","target_dialect":"json","projection":"data"}
      """;
    var request = HttpRequest.newBuilder(URI.create(base + "/v1/convert"))
      .header("content-type", "application/json")
      .POST(HttpRequest.BodyPublishers.ofString(json))
      .build();
    var response = HttpClient.newHttpClient().send(request, HttpResponse.BodyHandlers.ofString());
    if (response.statusCode() >= 300) throw new IllegalStateException(response.body());
    System.out.println(response.body());
  }
}
