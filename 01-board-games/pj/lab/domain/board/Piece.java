package domain.board;

public class Piece {

    private Location location;
    private PieceColor pieceColor;

    public Piece(Location location, PieceColor pieceColor) {
        this.location = location;
        this.pieceColor = pieceColor;
    }

    public Piece(int x, int y, PieceColor pieceColor) {
        this(new Location(x, y), pieceColor);
    }

    public Location getLocation() {
        return location;
    }

    public PieceColor getColor() {
        return pieceColor;
    }

    public boolean isOccupied() {
        return pieceColor != null;
    }
}
