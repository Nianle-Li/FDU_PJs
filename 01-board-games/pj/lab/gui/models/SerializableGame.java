package gui.models;

import java.io.Serializable;
import domain.board.PieceColor;
import java.util.Map;

/**
 * 可序列化的游戏数据类
 */
public class SerializableGame implements Serializable {
    private static final long serialVersionUID = 1L;
    
    private String gameType;
    private PieceColor[][] boardState;
    private int boardSize;
    private PieceColor currentPlayer;
    private boolean finished;
    private PieceColor winner;
    
    // 用于存储游戏特定属性
    private Map<String, Serializable> additionalAttributes;
    
    public SerializableGame() {}
    
    // Getters and setters
    public String getGameType() { return gameType; }
    public void setGameType(String gameType) { this.gameType = gameType; }
    
    public PieceColor[][] getBoardState() { return boardState; }
    public void setBoardState(PieceColor[][] boardState) { this.boardState = boardState; }
    
    public int getBoardSize() { return boardSize; }
    public void setBoardSize(int boardSize) { this.boardSize = boardSize; }
    
    public PieceColor getCurrentPlayer() { return currentPlayer; }
    public void setCurrentPlayer(PieceColor currentPlayer) { this.currentPlayer = currentPlayer; }
    
    public boolean isFinished() { return finished; }
    public void setFinished(boolean finished) { this.finished = finished; }
    
    public PieceColor getWinner() { return winner; }
    public void setWinner(PieceColor winner) { this.winner = winner; }

    public Map<String, Serializable> getAdditionalAttributes() { return additionalAttributes; }
    public void setAdditionalAttributes(Map<String, Serializable> additionalAttributes) { this.additionalAttributes = additionalAttributes; }
}
