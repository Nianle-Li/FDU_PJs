package console.playground;

import domain.board.PieceColor;

public class Player {
    private final String username;
    private PieceColor pieceColor;

    public Player(String username, PieceColor pieceColor) {
        this.username = username;
        this.pieceColor = pieceColor;
    }

    public String getName() {
        return username;
    }

    public PieceColor getPieceColor() {
        return pieceColor;
    }

    @Override
    public String toString() {
        return username; 
    }
}
