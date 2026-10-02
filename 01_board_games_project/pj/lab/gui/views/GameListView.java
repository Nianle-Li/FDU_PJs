package gui.views;

import domain.game.Game;
import domain.game.GomokuGame;
import domain.game.PeaceGame;
import domain.game.ReversiGame;
import javafx.beans.InvalidationListener;
import javafx.collections.ObservableList;
import javafx.geometry.Pos; // Import Pos for alignment
import javafx.scene.control.ListCell;
import javafx.scene.control.ListView;

public class GameListView extends ListView<Game> {

    private static final double FIXED_CELL_HEIGHT = 27.5; // 从 28.0 调整为 27.5
    private static final double LIST_PADDING = 2.0; // ListView自身的边框和内边距的额外高度
    private static final double MIN_LIST_HEIGHT_EMPTY = 5.0; // 空列表时的最小高度

    private final InvalidationListener listChangeListener;

    public GameListView() {
        setCellFactory(list -> new GameListCell());
        setPrefWidth(200);

        this.listChangeListener = observable -> updateListViewHeight();

        // 监听项目列表本身的变化 (例如，当通过 setItems 设置一个全新的列表时)
        itemsProperty().addListener((obs, oldList, newList) -> {
            if (oldList != null) {
                oldList.removeListener(this.listChangeListener);
            }
            if (newList != null) {
                newList.addListener(this.listChangeListener);
                updateListViewHeight(); // 当新列表设置时立即更新高度
            } else {
                // 如果新列表为null，则设置最小高度
                setPrefHeight(MIN_LIST_HEIGHT_EMPTY);
            }
        });

        // 如果在构造时已经有项目 (例如通过 FXML <items> 标签设置), 也添加监听器
        if (getItems() != null) {
            getItems().addListener(listChangeListener);
        }
        updateListViewHeight(); // 初始化高度
    }

    private void updateListViewHeight() {
        ObservableList<Game> items = getItems();
        if (items == null || items.isEmpty()) {
            setPrefHeight(MIN_LIST_HEIGHT_EMPTY);
        } else {
            setPrefHeight(items.size() * FIXED_CELL_HEIGHT + LIST_PADDING);
        }
    }
    
    private static class GameListCell extends ListCell<Game> {
        private static final String GAME_FORMAT = "%d. %s";
        
        @Override
        protected void updateItem(Game game, boolean empty) {
            super.updateItem(game, empty);
            
            if (empty || game == null) {
                setText(null);
                setGraphic(null);
                setAlignment(Pos.CENTER_LEFT);
            } else {
                int index = getIndex() + 1; // 1-based indexing for user display
                setText(String.format(GAME_FORMAT, index, getGameTypeName(game)));
                setAlignment(Pos.CENTER);
                setGraphic(null);
            }
        }
        
        private String getGameTypeName(Game game) {
            // 优先使用GameFactory获取游戏显示名称
            if (domain.game.GameFactory.getSupportedGameTypes().contains(game.getGameType())) {
                return domain.game.GameFactory.getDisplayName(game.getGameType());
            }
            
            // 后备方案：基于instanceof判断
            if (game instanceof PeaceGame) {
                return "和平棋";
            } else if (game instanceof ReversiGame) {
                return "黑白棋";
            } else if (game instanceof GomokuGame) {
                return "五子棋";
            } else {
                return game.getGameType();
            }
        }
    }
}
