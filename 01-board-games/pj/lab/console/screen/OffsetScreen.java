package console.screen;

/**
 * 将一个屏幕的一部分模拟为一个新的屏幕
 */
public class OffsetScreen implements Screen {
    private Screen screen;
    private int offsetRow;
    private int offsetCol;
    public OffsetScreen(Screen screen, int offsetRow, int offsetCol) {
        this.screen = screen;
        this.offsetRow = offsetRow;
        this.offsetCol = offsetCol;
    }
    @Override
    public void print(int row, int col, char c) {
        screen.print(row + offsetRow, col + offsetCol, c);
    }
    @Override
    public void print(int row, int col, String s) {
        screen.print(row + offsetRow, col + offsetCol, s);
    }

    @Override
    public void outputToConsole() {
        screen.outputToConsole();
    }
}
