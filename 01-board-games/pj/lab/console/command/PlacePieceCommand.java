package console.command;

import console.playground.PlayGround;
import console.playground.Player;
import domain.game.Game;

abstract public class PlacePieceCommand implements Command {
    private final Game game;
    private final PlayGround session;

    public PlacePieceCommand(Game game, PlayGround session) {
        this.game = game;
        this.session = session;
    }

    @Override
    public void execute(String args) {
        // 解析十六进制行号(1-F)和列号(A-O)
        char rowChar = Character.toUpperCase(args.charAt(0));
        int x;
        if (rowChar >= '1' && rowChar <= '9') {
            x = rowChar - '1';
        } else if (rowChar >= 'A' && rowChar <= 'F') {
            x = (rowChar - 'A') + 9;
        } else {
            throw new IllegalArgumentException("无效的行号: " + rowChar);
        }
        
        int y = Character.toUpperCase(args.charAt(1)) - 'A';
        game.placePiece(x, y);
    }

    @Override
    public boolean canAccept(String input) {
        if (input.length() != 2)
            return false;
        
        char rowChar = Character.toUpperCase(input.charAt(0));
        char colChar = Character.toUpperCase(input.charAt(1));
        
        boolean validRow = (rowChar >= '1' && rowChar <= '9') || (rowChar >= 'A' && rowChar <= 'F');
        boolean validCol = colChar >= 'A' && colChar <= 'O';
        
        return validRow && validCol;
    }

    @Override
    public String prompt() {
        //获取当前玩家
        Player currentPlayer = session.getPlayer(game.getCurrentPlayer());
        return String.format("请玩家[%s]输入落子位置(1A)", currentPlayer.getName());
    }

    @Override
    abstract public boolean isEnabled();
}
