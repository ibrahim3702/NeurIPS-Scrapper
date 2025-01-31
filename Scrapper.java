package pkg;
import org.jsoup.Jsoup;
import org.jsoup.nodes.Document;
import org.jsoup.nodes.Element;
import org.jsoup.select.Elements;

import java.io.File;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.nio.file.Files;
import java.nio.file.Paths;
import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.TimeUnit;

public class Scrapper {

    private static final String BASE_URL = "https://papers.nips.cc";
    private static final String OUTPUT_DIR = "D:\\scrapped-pdf2"; // Update with your desired path
    private static final int MAX_RETRIES = 3;
    private static final int TIMEOUT = 60; // seconds
    private static final int PROCESS_THREADS = 20;
    private static final int DOWNLOAD_THREADS = 20;

    private final HttpClient client;
    private final ExecutorService processExecutor;
    private final ExecutorService downloadExecutor;

    public Scrapper() {
        client = HttpClient.newBuilder().connectTimeout(java.time.Duration.ofSeconds(TIMEOUT))
                .build();
        processExecutor = Executors.newFixedThreadPool(PROCESS_THREADS);
        downloadExecutor = Executors.newFixedThreadPool(DOWNLOAD_THREADS);

        try {
            Files.createDirectories(Paths.get(OUTPUT_DIR));
        } catch (IOException e) {
            System.err.println("Failed to create output directory: " + e.getMessage());
            System.exit(1);
        }
    }

    private Document fetchPage(String url) throws IOException, InterruptedException {
        for (int i = 0; i <= MAX_RETRIES; i++) {
            try {
                HttpRequest request = HttpRequest.newBuilder(URI.create(url)).GET().build();
                HttpResponse<String> response = client.send(request, HttpResponse.BodyHandlers.ofString());
                if (response.statusCode() >= 200 && response.statusCode() < 300) {
                    return Jsoup.parse(response.body());
                } else if (response.statusCode() >= 500 && response.statusCode() < 600 && i < MAX_RETRIES) {
                    System.out.println("Retrying " + url + " (attempt " + (i + 1) + ")");
                    Thread.sleep(1000 * (long) Math.pow(2, i)); // Exponential backoff
                } else {
                    System.err.println("Failed to fetch " + url + ": " + response.statusCode());
                    return null;
                }
            } catch (IOException | InterruptedException e) {
                if (i < MAX_RETRIES) {
                    System.out.println("Retrying " + url + " (attempt " + (i + 1) + "): " + e.getMessage());
                    Thread.sleep(1000 * (long) Math.pow(2, i)); // Exponential backoff
                } else {
                    throw e; // Re-throw after max retries
                }
            }

        }
        return null; // Should not happen if retries work
    }


    private List<String> getYearlyProceedingsLinks() throws IOException, InterruptedException {
        Document soup = fetchPage(BASE_URL);
        if (soup == null) {
            return new ArrayList<>();
        }

        return soup.select("a[href^='/paper_files/paper/']").stream()
                .map(a -> BASE_URL + a.attr("href"))
                .toList();
    }

    private List<String> getPaperLinks(String yearUrl) throws IOException, InterruptedException {
        Document soup = fetchPage(yearUrl);
        if (soup == null) {
            return new ArrayList<>();
        }
        Element paperList = soup.selectFirst(".paper-list"); // Use CSS selector for class
        if (paperList == null) return new ArrayList<>(); // handle null case
        return paperList.select("a").stream()
                .map(a -> BASE_URL + a.attr("href"))
                .toList();
    }

    private void downloadPDF(String pdfUrl, String filename) {
        try {
            HttpRequest request = HttpRequest.newBuilder(URI.create(pdfUrl)).GET().build();
            HttpResponse<InputStream> response = client.send(request, HttpResponse.BodyHandlers.ofInputStream());
            if (response.statusCode() >= 200 && response.statusCode() < 300) {
                try (InputStream in = response.body();
                     FileOutputStream out = new FileOutputStream(new File(OUTPUT_DIR, filename + ".pdf"))) {
                    byte[] buffer = new byte[8192];
                    int bytesRead;
                    while ((bytesRead = in.read(buffer)) != -1) {
                        out.write(buffer, 0, bytesRead);
                    }
                    System.out.println("Saved PDF: " + filename + ".pdf");
                }
            } else {
                System.err.println("Failed to download " + pdfUrl + ": " + response.statusCode());
            }
        } catch (IOException | InterruptedException e) {
            System.err.println("Failed to download " + pdfUrl + ": " + e.getMessage());
        }
    }

    private void processPaper(String paperUrl) throws IOException, InterruptedException {

        System.out.println("Processing paper: " + paperUrl);
        Document soup = fetchPage(paperUrl);
        if (soup == null) return;


        Element titleTag = soup.selectFirst("h4"); // Use selectFirst for single element
        String paperTitle = titleTag != null ? titleTag.text().strip() : "Untitled";
        String sanitizedTitle = sanitizeFilename(paperTitle);

        Element pdfLink = soup.selectFirst("a[href$='.pdf']");
        if (pdfLink != null) {
            String pdfUrl = BASE_URL + pdfLink.attr("href");
            System.out.println("Found PDF link: " + pdfUrl);
            downloadExecutor.submit(() -> downloadPDF(pdfUrl, sanitizedTitle)); // Submit to download executor
        } else {
            System.out.println("No PDF found for " + paperUrl);
        }
    }

    private String sanitizeFilename(String filename) {
        return filename.replaceAll("[^a-zA-Z0-9 -]", "_"); // Use regex for sanitization
    }

    public void run() throws IOException, InterruptedException {
        List<String> yearlyLinks = getYearlyProceedingsLinks();
        System.out.println("Found " + yearlyLinks.size() + " yearly proceedings.");

        List<String> paperLinks = new ArrayList<>();
        for (String yearLink : yearlyLinks) {
            System.out.println("Fetching paper links for year: " + yearLink);
            paperLinks.addAll(getPaperLinks(yearLink));
        }

        System.out.println("Found " + paperLinks.size() + " total papers.");



        List<CompletableFuture<Void>> processFutures = paperLinks.stream()
                .map(link -> CompletableFuture.runAsync(() -> {
                    try {
                        processPaper(link);
                    } catch (IOException | InterruptedException e) {
                        System.err.println("Error processing paper link: " + e.getMessage());
                    }
                }, processExecutor))
                .toList();

        CompletableFuture.allOf(processFutures.toArray(new CompletableFuture[0])).join();

        processExecutor.shutdown();
        downloadExecutor.shutdown();

        try {
            processExecutor.awaitTermination(1, TimeUnit.MINUTES); // Adjust timeout as needed
            downloadExecutor.awaitTermination(1, TimeUnit.MINUTES);
        } catch (InterruptedException e) {
            System.err.println("Executor shutdown interrupted: " + e.getMessage());
        }

        System.out.println("All downloads initiated.");
    }

    public static void main(String[] args) throws IOException, InterruptedException {
        Scrapper downloader = new Scrapper();
        downloader.run();
    }
}
