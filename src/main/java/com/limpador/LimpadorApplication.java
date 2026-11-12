package com.limpador;

import com.limpador.util.PlatformUtils;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.boot.web.servlet.context.ServletWebServerApplicationContext;
import org.springframework.boot.context.event.ApplicationReadyEvent;
import org.springframework.context.event.EventListener;

import java.awt.Desktop;
import java.io.File;
import java.net.URI;
import java.util.List;

@SpringBootApplication
public class LimpadorApplication {

    public static void main(String[] args) {
        // Habilita modo headless seguro caso rode em ambiente sem interface gráfica
        System.setProperty("java.awt.headless", "false");
        SpringApplication.run(LimpadorApplication.class, args);
    }

    @EventListener(ApplicationReadyEvent.class)
    public void onApplicationReady(ApplicationReadyEvent event) {
        if (!(event.getApplicationContext() instanceof ServletWebServerApplicationContext webContext)) {
            System.err.println("Nao foi possivel detectar o servidor web para abrir o Limpador-PC.");
            return;
        }
        int port = webContext.getWebServer().getPort();
        String appUrl = "http://127.0.0.1:" + port;
        System.out.println("==========================================================");
        System.out.println("  🧹 Limpador-PC Pro (Spring Boot + Java 21)");
        System.out.println("  Servidor ativo em: " + appUrl);
        System.out.println("==========================================================");

        new Thread(() -> {
            try {
                Thread.sleep(800); // Aguarda inicialização do Tomcat
                openDesktopWindow(appUrl);
            } catch (Exception e) {
                System.err.println("Aviso ao abrir janela: " + e.getMessage());
            }
        }).start();
    }

    private static void openDesktopWindow(String url) {
        String browserBin = findChromiumBrowser();
        if (browserBin != null) {
            try {
                ProcessBuilder pb = new ProcessBuilder(
                        browserBin,
                        "--app=" + url,
                        "--window-size=1180,800"
                );
                pb.start();
                return;
            } catch (Exception ignored) {
            }
        }

        // Fallback: Navegador padrão do sistema operacional
        try {
            if (Desktop.isDesktopSupported() && Desktop.getDesktop().isSupported(Desktop.Action.BROWSE)) {
                Desktop.getDesktop().browse(new URI(url));
            }
        } catch (Exception ignored) {
        }
    }

    private static String findChromiumBrowser() {
        if (PlatformUtils.isWindows()) {
            List<String> candidates = List.of(
                    System.getenv("ProgramFiles(x86)") + "\\Microsoft\\Edge\\Application\\msedge.exe",
                    System.getenv("ProgramFiles") + "\\Microsoft\\Edge\\Application\\msedge.exe",
                    System.getenv("ProgramFiles") + "\\Google\\Chrome\\Application\\chrome.exe",
                    System.getenv("ProgramFiles(x86)") + "\\Google\\Chrome\\Application\\chrome.exe",
                    System.getenv("LocalAppData") + "\\Google\\Chrome\\Application\\chrome.exe",
                    System.getenv("ProgramFiles") + "\\BraveSoftware\\Brave-Browser\\Application\\brave.exe"
            );
            for (String p : candidates) {
                if (p != null && new File(p).isFile()) {
                    return p;
                }
            }
        } else if (PlatformUtils.isMac()) {
            List<String> candidates = List.of(
                    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
                    "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
                    "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser"
            );
            for (String p : candidates) {
                if (new File(p).isFile()) {
                    return p;
                }
            }
        } else { // Linux
            for (String cmd : List.of("google-chrome", "chromium-browser", "chromium", "brave-browser")) {
                try {
                    Process proc = new ProcessBuilder("which", cmd).start();
                    if (proc.waitFor() == 0) {
                        return cmd;
                    }
                } catch (Exception ignored) {
                }
            }
        }
        return null;
    }
}
