package gui.views;

import domain.board.Board;
import domain.board.Location;
import domain.board.PieceColor;
import javafx.scene.canvas.Canvas;
import javafx.scene.canvas.GraphicsContext;
import javafx.scene.input.MouseEvent;
import javafx.scene.layout.Pane;
import javafx.scene.paint.Color;
import javafx.scene.text.Font;
import javafx.scene.text.TextAlignment;

import java.util.ArrayList;
import java.util.List;
import java.util.function.BiConsumer;

public class BoardView extends Pane {
    private Canvas canvas;
    private Board board;
    private double cellSize;
    private BiConsumer<Integer, Integer> cellClickHandler;
    private List<Location> highlightedCells = new ArrayList<>();
    private boolean bombMode = false;
    
    // 棋盘尺寸配置常量
    private static final double SMALL_BOARD_PIECE_SIZE = 0.7; // 8x8棋盘的棋子大小比例
    private static final double LARGE_BOARD_PIECE_SIZE = 0.8; // 15x15棋盘的棋子大小比例

    public BoardView() {
        canvas = new Canvas();
        getChildren().add(canvas);
        
        canvas.setOnMouseClicked(this::handleMouseClick);
        
        // 响应大小变化
        widthProperty().addListener((obs, oldVal, newVal) -> redraw());
        heightProperty().addListener((obs, oldVal, newVal) -> redraw());
    }
    
    // 更新棋盘数据并重绘
    public void updateBoard(Board board) {
        this.board = board;
        redraw();
    }
    
    // 设置单元格点击事件处理器
    public void setOnCellClicked(BiConsumer<Integer, Integer> handler) {
        this.cellClickHandler = handler;
    }
    
    // 高亮显示可选位置
    public void highlightValidMoves(List<Location> locations) {
        this.highlightedCells = new ArrayList<>(locations);
        redraw();
    }
    
    // 清除所有高亮显示
    public void clearHighlights() {
        this.highlightedCells.clear();
        redraw();
    }
    
    // 设置炸弹放置模式
    public void setBombMode(boolean bombMode) {
        this.bombMode = bombMode;
        setCursor(bombMode ? javafx.scene.Cursor.CROSSHAIR : javafx.scene.Cursor.DEFAULT);
        redraw();
    }
    
    // 获取当前是否为炸弹模式
    public boolean isBombMode() {
        return bombMode;
    }
    
    // 处理鼠标点击事件
    private void handleMouseClick(MouseEvent event) {
        if (board == null || cellClickHandler == null) return;
        
        Location clickedLocation = getLocationFromClick(event.getX(), event.getY());
        if (clickedLocation != null) {
            cellClickHandler.accept(clickedLocation.getX(), clickedLocation.getY());
        }
    }
    
    // 根据点击坐标获取棋盘位置
    private Location getLocationFromClick(double clickX, double clickY) {
        double gridStartX = cellSize;
        double gridStartY = cellSize;
        double gridEndX = cellSize * (board.getSize() + 1);
        double gridEndY = cellSize * (board.getSize() + 1);
        
        if (clickX >= gridStartX && clickX < gridEndX && 
            clickY >= gridStartY && clickY < gridEndY) {
            
            int col = (int)((clickX - gridStartX) / cellSize);
            int row = (int)((clickY - gridStartY) / cellSize);
            
            if (row >= 0 && row < board.getSize() && col >= 0 && col < board.getSize()) {
                return Location.of(row, col);
            }
        }
        return null;
    }
    
    // 重绘整个棋盘
    private void redraw() {
        if (board == null) return;
        
        double width = getWidth();
        double height = getHeight();
        
        canvas.setWidth(width);
        canvas.setHeight(height);
        cellSize = Math.min(width, height) / (board.getSize() + 1);
        
        GraphicsContext gc = canvas.getGraphicsContext2D();
        gc.clearRect(0, 0, width, height);
        
        drawBoard(gc);
        drawLabels(gc);
        drawHighlights(gc);
        drawPieces(gc);
    }
    
    // 绘制棋盘背景和网格线
    private void drawBoard(GraphicsContext gc) {
        // 绘制棋盘背景
        gc.setFill(Color.PEACHPUFF);
        gc.fillRect(cellSize, cellSize, board.getSize() * cellSize, board.getSize() * cellSize);
        
        // 绘制网格线
        gc.setStroke(Color.BLACK);
        gc.setLineWidth(1.0);
        
        for (int i = 0; i <= board.getSize(); i++) {
            double pos = cellSize * (i + 1);
            gc.strokeLine(cellSize, pos, cellSize * (board.getSize() + 1), pos);
            gc.strokeLine(pos, cellSize, pos, cellSize * (board.getSize() + 1));
        }
    }
    
    // 绘制棋盘边缘的行列标签
    private void drawLabels(GraphicsContext gc) {
        gc.setFill(Color.BLACK);
        gc.setTextAlign(TextAlignment.CENTER);
        gc.setFont(new Font(cellSize * 0.5));
        
        // 行标签
        for (int i = 0; i < board.getSize(); i++) {
            String label = (i < 9) ? String.valueOf(i + 1) : String.valueOf((char)('A' + (i - 9)));
            gc.fillText(label, cellSize * 0.5, cellSize * (i + 1.5));
        }
        
        // 列标签
        for (int i = 0; i < board.getSize(); i++) {
            char label = (char)('A' + i);
            gc.fillText(String.valueOf(label), cellSize * (i + 1.5), cellSize * 0.5);
        }
    }
    
    // 绘制高亮提示标记
    private void drawHighlights(GraphicsContext gc) {
        if (!highlightedCells.isEmpty()) {
            gc.setStroke(Color.DIMGRAY);
            gc.setLineWidth(3.0);

            for (Location loc : highlightedCells) {
                double centerX = cellSize * (loc.getY() + 1.5);
                double centerY = cellSize * (loc.getX() + 1.5);
                double plusArmLength = cellSize * 0.2;

                // 绘制 "+" 号
                gc.strokeLine(centerX - plusArmLength, centerY, centerX + plusArmLength, centerY);
                gc.strokeLine(centerX, centerY - plusArmLength, centerX, centerY + plusArmLength);
            }
        }
    }
    
    // 绘制所有棋子
    private void drawPieces(GraphicsContext gc) {
        double pieceSizeMultiplier = (board.getSize() == 8) ? SMALL_BOARD_PIECE_SIZE : LARGE_BOARD_PIECE_SIZE;
        double size = cellSize * pieceSizeMultiplier;
        
        for (int row = 0; row < board.getSize(); row++) {
            for (int col = 0; col < board.getSize(); col++) {
                PieceColor piece = board.getPiece(row, col);
                if (piece != null) {
                    drawPiece(gc, row, col, piece, size);
                }
            }
        }
    }
    
    // 绘制单个棋子
    private void drawPiece(GraphicsContext gc, int row, int col, PieceColor pieceColor, double size) {
        double x = cellSize * (col + 1) + (cellSize - size) / 2;
        double y = cellSize * (row + 1) + (cellSize - size) / 2;
        
        switch (pieceColor) {
            case BLACK -> {
                gc.setFill(Color.BLACK);
                gc.fillOval(x, y, size, size);
            }
            case WHITE -> {
                gc.setFill(Color.IVORY);
                gc.fillOval(x, y, size, size);
            }
            case BARRIER -> {
                gc.setFill(Color.DARKGRAY);
                gc.fillRect(x, y, size, size);
            }
            case BOMB_CRATER -> {
                gc.setFill(Color.RED);
                gc.fillOval(x, y, size, size);
                drawExplosionEffect(gc, x + size/2, y + size/2, size/2 * 0.7);
            }
        }
    }
    
    // 绘制爆炸效果（用于炸弹坑）
    private void drawExplosionEffect(GraphicsContext gc, double centerX, double centerY, double rayLength) {
        gc.setStroke(Color.ORANGERED);
        gc.setLineWidth(2);
        
        for (int i = 0; i < 8; i++) {
            double angle = i * Math.PI / 4;
            gc.strokeLine(
                centerX, centerY,
                centerX + rayLength * Math.cos(angle),
                centerY + rayLength * Math.sin(angle)
            );
        }
    }
}
