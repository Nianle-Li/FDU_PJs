package console.gameview;

import java.util.ArrayList;
import java.util.List;

import console.BoardViewer;
import console.command.Command;
import console.command.NewGameCommand;
import console.command.PlacePieceCommand;
import console.command.QuitCommand;
import console.command.SelectGameCommand;
import console.playground.PlayGround;
import console.screen.Screen;
import domain.board.Location;
import domain.game.Game;
import domain.game.PeaceGame;

public class PeaceGameView extends GameViewer {
    PeaceGame game;
    BoardViewer boardConsole;

    public static PeaceGameView create() {
        return new PeaceGameView(new PeaceGame());
    }

    @Override
    public Game getGame() {
        return game;
    }   

    public PeaceGameView(PeaceGame game, String gameDesc) {
        super(gameDesc);
        this.game = game;
        this.boardConsole = new BoardViewer(game.getBoard());
    }

    public PeaceGameView(PeaceGame game) {
        this(game, "");
    }

    @Override
    public void showBoard(Screen screen) {
        boardConsole.display(screen);
    }

    @Override
    public String getGameStatus() {
        if (game.isOver()) {
            return "游戏结束: 平局";
        } else {
            return "";
        }
    }
    
    @Override
    public List<Command> getCommandList(PlayGround session) {
        List<Command> commands = new ArrayList<>();
        
        // 添加游戏特定命令
        commands.add(new PlacePieceCommand(game, session) {
            @Override
            public boolean isEnabled() {
                return !game.isOver();
            }
        });
        commands.add(new SelectGameCommand(session));
        commands.add(new NewGameCommand(session));
        commands.add(new QuitCommand());
        
        // 添加通用命令
        commands.addAll(getCommonCommands(session));
        
        return commands;
    }

    @Override
    public Location getSize() {
        return Location.of(game.getBoard().getSize(), game.getBoard().getSize());
    }

}
