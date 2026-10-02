package gui;

import gui.controllers.MainController;
import gui.models.GameStateManager;
import javafx.application.Application;
import javafx.application.Platform;
import javafx.fxml.FXMLLoader;
import javafx.scene.Parent;
import javafx.scene.Scene;
import javafx.stage.Stage;

public class BoardGameApp extends Application {

    @Override
    public void start(Stage primaryStage) throws Exception {
        try {
            // 使用绝对路径方式加载FXML
            FXMLLoader loader = new FXMLLoader(getClass().getResource("/fxml/main.fxml"));
            
            if (loader.getLocation() == null) {
                // 如果找不到资源，输出错误信息
                System.err.println("Error: Could not find FXML file at /fxml/main.fxml");
                System.err.println("Current classpath: " + System.getProperty("java.class.path"));
                throw new IllegalStateException("FXML resource not found");
            }
            
            Parent root = loader.load();
            
            MainController controller = loader.getController();
            controller.initialize();
            
            Scene scene = new Scene(root, 1200, 700); // 将宽度从 900 调整为 1200
            
            // 尝试加载CSS，如果找不到则跳过
            try {
                String cssResource = "/css/styles.css";
                if (getClass().getResource(cssResource) != null) {
                    scene.getStylesheets().add(getClass().getResource(cssResource).toExternalForm());
                } else {
                    System.out.println("Warning: CSS file not found, using default styles");
                }
            } catch (Exception e) {
                System.err.println("Warning: Could not load CSS: " + e.getMessage());
            }
            
            primaryStage.setTitle("棋类游戏");
            primaryStage.setScene(scene);
            primaryStage.setResizable(true);
            
            // 设置窗口关闭事件
            primaryStage.setOnCloseRequest(event -> {
                // 保存游戏状态
                if (controller != null && controller.getGameSession() != null) {
                    GameStateManager.saveGameState(controller.getGameSession());
                }
                Platform.exit();
            });
            
            primaryStage.show();
        } catch (Exception e) {
            System.err.println("Error during application startup: " + e.getMessage());
            e.printStackTrace();
            throw e;
        }
    }

    public static void main(String[] args) {
        launch(args);
    }
}
