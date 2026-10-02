package console;

import console.screen.Screen;
import domain.board.Board;
import domain.board.PieceColor;

public class BoardViewer {
    private Board board;

    public BoardViewer(Board board) {
        this.board = board;
    }

    public void display(Screen screen) {
        int size = board.getSize();
        // 列标题
        for (int j = 0; j < size; j++) {
            screen.print(0, 2 + j * 2, (char) ('A' + j));
        }
        // 棋盘内容
        for (int i = 0; i < size; i++) {
            // 行号 - 使用十六进制(1-F)表示
            char rowChar;
            if (i < 9) {
                rowChar = (char)('1' + i);
            } else {
                rowChar = (char)('A' + (i - 9));
            }
            screen.print(i + 1, 0, rowChar);
            screen.print(i + 1, 1, ' ');
            for (int j = 0; j < size; j++) {
                PieceColor piece = board.getPiece(i, j);
                char c = '·';
                if (piece == PieceColor.BLACK)
                    c = '●';
                else if (piece == PieceColor.WHITE)
                    c = '○';
                else if (piece == PieceColor.BARRIER)
                    c = '#';  // 障碍物显示为#
                else if (piece == PieceColor.BOMB_CRATER)
                    c = '@';  // 弹坑显示为@
                screen.print(i + 1, 2 + j * 2, c);
                // 每格后加空格
                if (2 + j * 2 + 1 < board.getSize())
                    screen.print(i + 1, 2 + j * 2 + 1, ' ');
            }
        }
    }

}
