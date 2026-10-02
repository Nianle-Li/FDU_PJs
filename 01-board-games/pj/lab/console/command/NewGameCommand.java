package console.command;

import java.util.List;

import console.gameview.GomokuGameView;
import console.gameview.PeaceGameView;
import console.gameview.ReversiGameView;
import console.playground.PlayGround;
import domain.game.GomokuGame;
import domain.game.PeaceGame;
import domain.game.ReversiGame;

public class NewGameCommand implements Command {
    private static final List<String> COMMANDS = List.of("peace", "gomoku", "reversi");
    private final PlayGround session;

    public NewGameCommand(PlayGround session) {
        this.session = session;
    }

    @Override
    public void execute(String cmd) {
        if (cmd.equals("peace")) {
            session.addGame(new PeaceGameView(new PeaceGame()));
        } else if (cmd.equals("gomoku")) {
            session.addGame(new GomokuGameView(new GomokuGame()));
        } else if (cmd.equals("reversi")) {
            session.addGame(new ReversiGameView(new ReversiGame()));
        } else {
            throw new RuntimeException("Invalid command");
        }
    }

    @Override
    public boolean canAccept(String input) {
        return COMMANDS.contains(input);
    }

    @Override
    public String prompt() {
        return String.format("新游戏(%s)", String.join("/", COMMANDS));
    }

    @Override
    public boolean isEnabled() {
        return true;
    }
}
