package gui.models;

import java.io.Serializable;
import java.util.List;

/**
 * 游戏会话状态类，用于序列化保存游戏状态
 */
public class GameState implements Serializable {
    private static final long serialVersionUID = 1L;
    
    private String player1Name;
    private String player2Name;
    private List<SerializableGame> games;
    private int currentGameIndex;
    
    public GameState() {}
    
    public GameState(String player1Name, String player2Name, List<SerializableGame> games, int currentGameIndex) {
        this.player1Name = player1Name;
        this.player2Name = player2Name;
        this.games = games;
        this.currentGameIndex = currentGameIndex;
    }
    
    // Getters and setters
    public String getPlayer1Name() { return player1Name; }
    public void setPlayer1Name(String player1Name) { this.player1Name = player1Name; }
    
    public String getPlayer2Name() { return player2Name; }
    public void setPlayer2Name(String player2Name) { this.player2Name = player2Name; }
    
    public List<SerializableGame> getGames() { return games; }
    public void setGames(List<SerializableGame> games) { this.games = games; }
    
    public int getCurrentGameIndex() { return currentGameIndex; }
    public void setCurrentGameIndex(int currentGameIndex) { this.currentGameIndex = currentGameIndex; }
}
