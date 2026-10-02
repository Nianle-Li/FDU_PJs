package console.command;

import console.playground.PlayGround;
import domain.board.Location;
import domain.game.GomokuGame;

public class UseBombCommand implements Command {
    private final GomokuGame game;
    private final PlayGround session;

    public UseBombCommand(GomokuGame game, PlayGround session) {
        this.game = game;
        this.session = session;
    }

    @Override
    public void execute(String args) {
        // 移除@符号并解析位置
        String position = args.substring(1);
        char rowChar = Character.toUpperCase(position.charAt(0));
        int x;
        
        if (rowChar >= '1' && rowChar <= '9') {
            x = rowChar - '1';
        } else if (rowChar >= 'A' && rowChar <= 'F') {
            x = (rowChar - 'A') + 9;
        } else {
            throw new IllegalArgumentException("无效的行号: " + rowChar);
        }
        
        int y = Character.toUpperCase(position.charAt(1)) - 'A';
        game.useBomb(Location.of(x, y));
    }

    @Override
    public boolean canAccept(String input) {
        if (input.length() != 3 || input.charAt(0) != '@')
            return false;
        
        String position = input.substring(1);
        if (position.length() != 2)
            return false;
            
        char rowChar = Character.toUpperCase(position.charAt(0));
        char colChar = Character.toUpperCase(position.charAt(1));
        
        boolean validRow = (rowChar >= '1' && rowChar <= '9') || (rowChar >= 'A' && rowChar <= 'F');
        boolean validCol = colChar >= 'A' && colChar <= 'O';
        
        return validRow && validCol;
    }

    @Override
    public String prompt() {
        return String.format("使用炸弹(@FA)");
    }

    @Override
    public boolean isEnabled() {
        return !game.isOver() && game.getCurrentPlayerBombs() > 0;
    }
}
