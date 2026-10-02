package gui.models;

import domain.board.PieceColor;
import domain.game.Game;
import domain.game.PeaceGame;
import domain.game.ReversiGame;
import domain.game.GomokuGame;
import javafx.collections.FXCollections;
import javafx.collections.ObservableList;
import javafx.beans.property.IntegerProperty;
import javafx.beans.property.SimpleIntegerProperty;
import java.util.List;

public class GameSession {
    private final String player1Name;
    private final String player2Name;
    private final ObservableList<Game> games = FXCollections.observableArrayList();
    private final IntegerProperty currentGameIndex = new SimpleIntegerProperty(0);

    public GameSession(String player1Name, String player2Name) {
        this(player1Name, player2Name, true);
    }
    
    /**
     * 创建游戏会话（用于状态恢复）
     */
    public GameSession(String player1Name, String player2Name, boolean createDefaultGames) {
        this.player1Name = player1Name;
        this.player2Name = player2Name;
        
        if (createDefaultGames) {
            initializeDefaultGames();
        }
    }
    
    private void initializeDefaultGames() {
        games.addAll(List.of(
            new PeaceGame(),
            new ReversiGame(), 
            new GomokuGame()
        ));
    }
    
    public String getPlayer1Name() {
        return player1Name;
    }
    
    public String getPlayer2Name() {
        return player2Name;
    }
    
    public String getPlayerName(PieceColor color) {
        return color == PieceColor.BLACK ? player1Name : player2Name;
    }
    
    public ObservableList<Game> getGames() {
        return games;
    }
    
    public Game getCurrentGame() {
        if (games.isEmpty()) {
            return null;
        }
        return games.get(getCurrentGameIndex());
    }
    
    public int getCurrentGameIndex() {
        return currentGameIndex.get();
    }
    
    public IntegerProperty currentGameIndexProperty() {
        return currentGameIndex;
    }
    
    public void setCurrentGameIndex(int index) {
        if (index >= 0 && index < games.size()) {
            currentGameIndex.set(index);
        }
    }
    
    public void addGame(Game game) {
        games.add(game);
    }
    
    public boolean removeGame(int index) {
        if (index >= 0 && index < games.size() && games.size() > 1) {
            games.remove(index);
            // 调整当前游戏索引
            if (getCurrentGameIndex() >= games.size()) {
                setCurrentGameIndex(games.size() - 1);
            }
            return true;
        }
        return false;
    }
}
