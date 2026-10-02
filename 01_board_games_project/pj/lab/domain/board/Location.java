package domain.board;

public class Location {
    private int x;
    private int y;
    public Location(int x, int y) {
        this.x = x;
        this.y = y;
    }
    public int getX() {
        return x;
    }
    public int getY() {
        return y;
    }

    public static Location of(int x, int y) {
        return new Location(x, y);
    }

    public Location at(Direction direction) {
        return new Location(x + direction.getDx(), y + direction.getDy());
    }

    @Override
    public boolean equals(Object obj) {
        if (obj == null) {
            return false;
        }
        if (obj == this) {
            return true;
        }
        if (!(obj instanceof Location)) {
            return false;
        }
        Location other = (Location) obj;
        return other.getX() == this.getX() && other.getY() == this.getY();
    }

    @Override
    public String toString() {
        return String.format("(x:%d, y:%d)", getX(), getY());
    }
}
