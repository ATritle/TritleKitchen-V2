from __future__ import annotations

import json
import re
import shutil
import sys
from pathlib import Path

from PyQt6.QtCore import Qt, QSettings, QSize
from PyQt6.QtGui import QFont, QIcon, QPixmap, QImage, QImageReader
from PyQt6.QtWidgets import (
    QApplication,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSplitter,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

APP_NAME = "Tritle Kitchen Recipe Creator"
CATEGORIES = ["Breakfast", "Desserts", "Dinner", "Drinks", "Miscellaneous"]
JSON_FILES = {category: f"data/{category.lower()}.json" for category in CATEGORIES}
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}

GREEN = "#5fbd73"
GREEN_DARK = "#173b22"
GREEN_DEEP = "#102a18"
BLACK = "#0b0f0c"
PANEL = "#141b16"
PANEL_2 = "#1a241c"
BORDER = "#2c3d31"
TEXT = "#f2f5f1"
MUTED = "#9ba99e"
ORANGE = "#ff7a00"
RED = "#e05b5b"


STYLESHEET = f"""
QWidget {{
    background: {BLACK};
    color: {TEXT};
    font-size: 14px;
}}
QMainWindow {{ background: {BLACK}; }}
QLabel {{ background: transparent; }}
QLabel#title {{ font-size: 25px; font-weight: 700; }}
QLabel#subtitle {{ color: {MUTED}; font-size: 13px; }}
QLabel#sectionTitle {{ font-size: 17px; font-weight: 700; color: {GREEN}; }}
QLabel#status {{ color: {MUTED}; padding: 5px 0; }}
QFrame#card, QGroupBox {{
    background: {PANEL};
    border: 1px solid {BORDER};
    border-radius: 12px;
}}
QGroupBox {{ margin-top: 12px; padding: 18px 12px 12px 12px; }}
QGroupBox::title {{
    subcontrol-origin: margin;
    left: 14px;
    padding: 0 7px;
    color: {GREEN};
    font-weight: 700;
}}
QLineEdit, QComboBox, QTextEdit, QTableWidget, QListWidget {{
    background: {PANEL_2};
    border: 1px solid {BORDER};
    border-radius: 8px;
    padding: 7px;
    selection-background-color: {GREEN_DARK};
    selection-color: {TEXT};
}}
QLineEdit:focus, QComboBox:focus, QTextEdit:focus, QTableWidget:focus, QListWidget:focus {{
    border: 1px solid {GREEN};
}}
QComboBox::drop-down {{ border: 0; width: 28px; }}
QPushButton {{
    background: {PANEL_2};
    border: 1px solid {BORDER};
    border-radius: 8px;
    padding: 9px 14px;
    min-height: 18px;
}}
QPushButton:hover {{ border-color: {GREEN}; }}
QPushButton:pressed {{ background: {GREEN_DARK}; }}
QPushButton#primary {{
    background: {GREEN};
    color: #071009;
    border: 0;
    font-weight: 800;
    padding: 11px 18px;
}}
QPushButton#primary:hover {{ background: #76cf87; }}
QPushButton#danger {{ color: #ff9a9a; }}
QPushButton#orange {{ border-color: {ORANGE}; color: #ffb36e; }}
QTableWidget {{ gridline-color: {BORDER}; }}
QHeaderView::section {{
    background: {GREEN_DEEP};
    color: {TEXT};
    padding: 7px;
    border: 0;
    border-bottom: 1px solid {BORDER};
    font-weight: 700;
}}
QListWidget::item {{ padding: 7px; border-bottom: 1px solid {BORDER}; }}
QListWidget::item:selected {{ background: {GREEN_DARK}; }}
QScrollBar:vertical {{ background: {PANEL}; width: 12px; margin: 2px; }}
QScrollBar::handle:vertical {{ background: {BORDER}; border-radius: 6px; min-height: 25px; }}
QTabWidget::pane {{ border: 1px solid {BORDER}; border-radius: 10px; background: {PANEL}; }}
QTabBar::tab {{ background: {PANEL_2}; padding: 10px 16px; margin-right: 3px; border-radius: 8px; }}
QTabBar::tab:selected {{ background: {GREEN_DARK}; color: {GREEN}; }}
"""


def app_dir() -> Path:
    return Path(__file__).resolve().parent


def repo_candidates() -> list[Path]:
    here = app_dir()
    candidates = [here, *here.parents]
    # Also support launching a copied standalone version beside the repo.
    cwd = Path.cwd().resolve()
    candidates.extend([cwd, *cwd.parents])
    unique: list[Path] = []
    seen: set[Path] = set()
    for p in candidates:
        if p in seen:
            continue
        seen.add(p)
        unique.append(p)
    return unique


def find_project_root() -> Path | None:
    for candidate in repo_candidates():
        if (candidate / "data").is_dir() and (candidate / "assets" / "recipes").is_dir():
            if (candidate / "index.html").exists():
                return candidate
    return None


def slugify(value: str) -> str:
    value = value.strip().lower()
    value = value.replace("&", " and ")
    value = re.sub(r"['’]", "", value)
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return value.strip("-") or "recipe"


def normalize_name(value: str) -> str:
    return re.sub(r"^⭐\s*", "", value or "").strip().casefold()


def read_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"{path.name} must contain a JSON object at the top level.")
    return data


def write_json(path: Path, data: dict) -> None:
    # Keep the V2 JSON human-readable and stable for Git diffs.
    text = json.dumps(data, ensure_ascii=False, indent=2)
    path.write_text(text + "\n", encoding="utf-8")


class ImagePreview(QLabel):
    def __init__(self) -> None:
        super().__init__()
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setMinimumSize(280, 220)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setStyleSheet(
            f"background:{PANEL_2}; border:1px solid {BORDER}; border-radius:10px; color:{MUTED};"
        )
        self._pixmap = QPixmap()
        self.setText("No recipe photo selected")

    def set_image(self, path: Path | None) -> None:
        if not path or not path.exists():
            self._pixmap = QPixmap()
            self.setText("No recipe photo selected")
            self.setPixmap(QPixmap())
            return
        pixmap = QPixmap(str(path))
        if pixmap.isNull():
            self._pixmap = QPixmap()
            self.setText("Unable to preview image")
            self.setPixmap(QPixmap())
            return
        self._pixmap = pixmap
        self._refresh()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._refresh()

    def _refresh(self) -> None:
        if self._pixmap.isNull():
            return
        scaled = self._pixmap.scaled(
            self.size() - QSize(12, 12),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self.setPixmap(scaled)
        self.setText("")


class RecipeCreator(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.settings = QSettings("TritleKitchen", "RecipeCreator")
        self.project_root = self._load_initial_project()
        self.image_source: Path | None = None
        self.logo_path = app_dir() / "assets" / "tritlekitchenlogo.png"

        self.setWindowTitle(APP_NAME)
        self.resize(1280, 900)
        self.setMinimumSize(1050, 760)
        if self.logo_path.exists():
            self.setWindowIcon(QIcon(str(self.logo_path)))
        self.setStyleSheet(STYLESHEET)

        self._build_ui()
        self._refresh_subcategories()
        self._update_project_status()

    # ----------------------------- UI -----------------------------
    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(18, 16, 18, 14)
        root.setSpacing(12)

        header = QHBoxLayout()
        if self.logo_path.exists():
            logo = QLabel()
            logo.setPixmap(QPixmap(str(self.logo_path)).scaledToHeight(54, Qt.TransformationMode.SmoothTransformation))
            header.addWidget(logo)
        title_box = QVBoxLayout()
        title = QLabel(APP_NAME)
        title.setObjectName("title")
        subtitle = QLabel("Build a recipe once, then add it directly to the Tritle Kitchen V2 data files.")
        subtitle.setObjectName("subtitle")
        title_box.addWidget(title)
        title_box.addWidget(subtitle)
        header.addLayout(title_box)
        header.addStretch()
        project_btn = QPushButton("📁 Project")
        project_btn.clicked.connect(self.choose_project)
        header.addWidget(project_btn)
        root.addLayout(header)

        self.project_status = QLabel()
        self.project_status.setObjectName("status")
        root.addWidget(self.project_status)

        self.tabs = QStackedWidget()
        root.addWidget(self.tabs, 1)

        editor_page = QWidget()
        editor_layout = QVBoxLayout(editor_page)
        editor_layout.setContentsMargins(0, 0, 0, 0)
        editor_layout.setSpacing(10)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setChildrenCollapsible(False)
        splitter.addWidget(self._build_left_editor())
        splitter.addWidget(self._build_right_editor())
        splitter.setSizes([650, 550])
        editor_layout.addWidget(splitter, 1)

        bottom = QHBoxLayout()
        self.validation_label = QLabel("Ready")
        self.validation_label.setObjectName("status")
        bottom.addWidget(self.validation_label)
        bottom.addStretch()
        preview_btn = QPushButton("Preview JSON")
        preview_btn.clicked.connect(self.preview_json)
        bottom.addWidget(preview_btn)
        validate_btn = QPushButton("Validate")
        validate_btn.clicked.connect(self.validate_form)
        bottom.addWidget(validate_btn)
        clear_btn = QPushButton("Clear Form")
        clear_btn.clicked.connect(self.clear_form)
        bottom.addWidget(clear_btn)
        add_btn = QPushButton("ADD RECIPE TO TRITLE KITCHEN")
        add_btn.setObjectName("primary")
        add_btn.clicked.connect(self.add_recipe)
        bottom.addWidget(add_btn)
        editor_layout.addLayout(bottom)

        self.tabs.addWidget(editor_page)

    def _build_left_editor(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(0, 0, 8, 0)
        layout.setSpacing(12)

        basic = QGroupBox("Recipe Information")
        form = QFormLayout(basic)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        form.setVerticalSpacing(10)

        self.title_edit = QLineEdit()
        self.title_edit.setPlaceholderText("e.g. Chicken Parmesan")
        self.title_edit.textChanged.connect(self._update_preview_header)
        form.addRow("Recipe Title *", self.title_edit)

        self.subtitle_edit = QLineEdit()
        self.subtitle_edit.setPlaceholderText("Optional source, author, or short subtitle")
        form.addRow("Subtitle", self.subtitle_edit)

        self.category_combo = QComboBox()
        self.category_combo.addItems(CATEGORIES)
        self.category_combo.currentTextChanged.connect(self._refresh_subcategories)
        form.addRow("Category *", self.category_combo)

        self.subcategory_combo = QComboBox()
        self.subcategory_combo.setEditable(True)
        self.subcategory_combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.subcategory_combo.lineEdit().setPlaceholderText("Choose or type a sub-category")
        self.subcategory_combo.currentTextChanged.connect(lambda _x: self._update_preview_header())
        form.addRow("Sub-Category *", self.subcategory_combo)

        self.slug_label = QLabel("—")
        self.slug_label.setStyleSheet(f"color:{MUTED}; font-family:Consolas,monospace;")
        self.title_edit.textChanged.connect(lambda _x: self.slug_label.setText(slugify(self.title_edit.text()) or "—"))
        form.addRow("Recipe Slug", self.slug_label)
        layout.addWidget(basic)

        image_group = QGroupBox("Recipe Photo")
        image_layout = QVBoxLayout(image_group)
        image_row = QHBoxLayout()
        self.image_path_label = QLabel("No image selected")
        self.image_path_label.setObjectName("status")
        image_row.addWidget(self.image_path_label, 1)
        browse_image = QPushButton("Choose Photo…")
        browse_image.setObjectName("orange")
        browse_image.clicked.connect(self.choose_image)
        image_row.addWidget(browse_image)
        clear_image = QPushButton("Clear")
        clear_image.clicked.connect(self.clear_image)
        image_row.addWidget(clear_image)
        image_layout.addLayout(image_row)
        self.image_preview = ImagePreview()
        image_layout.addWidget(self.image_preview, 1)
        image_note = QLabel("JPG and PNG are recommended. Other common image types are converted to JPG when added.")
        image_note.setObjectName("subtitle")
        image_layout.addWidget(image_note)
        layout.addWidget(image_group, 1)

        ingredients_group = QGroupBox("Ingredients")
        ing_layout = QVBoxLayout(ingredients_group)
        self.ingredients = QTableWidget(0, 4)
        self.ingredients.setHorizontalHeaderLabels(["Amount", "Unit", "Ingredient *", "Note"])
        self.ingredients.horizontalHeader().setStretchLastSection(True)
        self.ingredients.setColumnWidth(0, 100)
        self.ingredients.setColumnWidth(1, 105)
        self.ingredients.setColumnWidth(2, 260)
        self.ingredients.setAlternatingRowColors(True)
        ing_layout.addWidget(self.ingredients, 1)
        ing_buttons = QHBoxLayout()
        for text, slot in [
            ("＋ Add Ingredient", self.add_ingredient),
            ("Remove", self.remove_ingredient),
            ("↑", lambda: self.move_ingredient(-1)),
            ("↓", lambda: self.move_ingredient(1)),
        ]:
            b = QPushButton(text)
            b.clicked.connect(slot)
            ing_buttons.addWidget(b)
        ing_buttons.addStretch()
        ing_layout.addLayout(ing_buttons)
        layout.addWidget(ingredients_group, 1)

        layout.addStretch()
        scroll.setWidget(content)
        return scroll

    def _build_right_editor(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(8, 0, 0, 0)
        layout.setSpacing(12)

        directions_group = QGroupBox("Directions")
        dir_layout = QVBoxLayout(directions_group)
        self.directions = QListWidget()
        self.directions.setAlternatingRowColors(True)
        self.directions.itemDoubleClicked.connect(lambda item: self._edit_direction_item(item))
        dir_layout.addWidget(self.directions, 1)
        dir_buttons = QHBoxLayout()
        add_dir = QPushButton("＋ Add Step")
        add_dir.clicked.connect(self.add_direction)
        dir_buttons.addWidget(add_dir)
        edit_dir = QPushButton("Edit")
        edit_dir.clicked.connect(self.edit_direction)
        dir_buttons.addWidget(edit_dir)
        remove_dir = QPushButton("Remove")
        remove_dir.setObjectName("danger")
        remove_dir.clicked.connect(self.remove_direction)
        dir_buttons.addWidget(remove_dir)
        up_dir = QPushButton("↑")
        up_dir.clicked.connect(lambda: self.move_direction(-1))
        dir_buttons.addWidget(up_dir)
        down_dir = QPushButton("↓")
        down_dir.clicked.connect(lambda: self.move_direction(1))
        dir_buttons.addWidget(down_dir)
        dir_buttons.addStretch()
        dir_layout.addLayout(dir_buttons)
        layout.addWidget(directions_group, 1)

        preview_group = QGroupBox("Recipe Preview")
        preview_layout = QVBoxLayout(preview_group)
        self.preview_title = QLabel("Recipe Title")
        self.preview_title.setStyleSheet(f"font-size:22px;font-weight:800;color:{GREEN};")
        preview_layout.addWidget(self.preview_title)
        self.preview_meta = QLabel("Category / Sub-Category")
        self.preview_meta.setObjectName("subtitle")
        preview_layout.addWidget(self.preview_meta)
        self.preview_json_box = QTextEdit()
        self.preview_json_box.setReadOnly(True)
        self.preview_json_box.setMinimumHeight(330)
        preview_layout.addWidget(self.preview_json_box, 1)
        layout.addWidget(preview_group, 1)

        note = QLabel(
            "When you add the recipe, the tool updates the selected category JSON, creates the image under "
            "assets/recipes, and keeps recipes alphabetized."
        )
        note.setObjectName("subtitle")
        note.setWordWrap(True)
        layout.addWidget(note)

        layout.addStretch()
        scroll.setWidget(content)
        return scroll

    # ----------------------------- Project -----------------------------
    def _load_initial_project(self) -> Path | None:
        saved = self.settings.value("project_root", "", str)
        if saved:
            p = Path(saved)
            if self._is_project_root(p):
                return p
        return find_project_root()

    @staticmethod
    def _is_project_root(path: Path) -> bool:
        return (path / "data").is_dir() and (path / "assets" / "recipes").is_dir() and (path / "index.html").exists()

    def choose_project(self) -> None:
        start = str(self.project_root or Path.home())
        selected = QFileDialog.getExistingDirectory(self, "Select TritleKitchen V2 Project Folder", start)
        if not selected:
            return
        path = Path(selected)
        if not self._is_project_root(path):
            QMessageBox.warning(
                self,
                "Not a Tritle Kitchen V2 Project",
                "The selected folder must contain index.html, data/, and assets/recipes/.",
            )
            return
        self.project_root = path
        self.settings.setValue("project_root", str(path))
        self._refresh_subcategories()
        self._update_project_status()

    def _update_project_status(self) -> None:
        if self.project_root:
            self.project_status.setText(f"Project: {self.project_root}")
        else:
            self.project_status.setText("Project: Not selected — click 📁 Project to choose your TritleKitchen V2 folder.")

    # ----------------------------- Data -----------------------------
    def _category_path(self, category: str) -> Path:
        if not self.project_root:
            raise ValueError("Select a Tritle Kitchen V2 project first.")
        return self.project_root / JSON_FILES[category]

    def _load_all_recipes(self) -> list[tuple[str, str, dict]]:
        records = []
        for category in CATEGORIES:
            path = self._category_path(category)
            if not path.exists():
                continue
            data = read_json(path)
            for subcategory, recipes in data.items():
                if not isinstance(recipes, list):
                    continue
                for recipe in recipes:
                    if isinstance(recipe, dict):
                        records.append((category, str(subcategory), recipe))
        return records

    def _refresh_subcategories(self) -> None:
        current = self.subcategory_combo.currentText() if hasattr(self, "subcategory_combo") else ""
        self.subcategory_combo.blockSignals(True)
        self.subcategory_combo.clear()
        try:
            if self.project_root:
                data = read_json(self._category_path(self.category_combo.currentText()))
                self.subcategory_combo.addItems(sorted(data.keys(), key=str.casefold))
        except Exception:
            pass
        self.subcategory_combo.setCurrentText(current)
        self.subcategory_combo.blockSignals(False)
        self._update_preview_header()

    # ----------------------------- Image -----------------------------
    def choose_image(self) -> None:
        filename, _ = QFileDialog.getOpenFileName(
            self,
            "Choose Recipe Photo",
            str(Path.home()),
            "Recipe Images (*.jpg *.jpeg *.png *.webp *.bmp);;All Files (*.*)",
        )
        if not filename:
            return
        self.image_source = Path(filename)
        self.image_path_label.setText(str(self.image_source))
        self.image_preview.set_image(self.image_source)

    def clear_image(self) -> None:
        self.image_source = None
        self.image_path_label.setText("No image selected")
        self.image_preview.set_image(None)

    # ----------------------------- Ingredients -----------------------------
    def add_ingredient(self) -> None:
        row = self.ingredients.rowCount()
        self.ingredients.insertRow(row)
        self.ingredients.setItem(row, 0, QTableWidgetItem(""))
        self.ingredients.setItem(row, 1, QTableWidgetItem("each"))
        self.ingredients.setItem(row, 2, QTableWidgetItem(""))
        self.ingredients.setItem(row, 3, QTableWidgetItem(""))
        self.ingredients.setCurrentCell(row, 2)
        self.ingredients.editItem(self.ingredients.item(row, 2))

    def remove_ingredient(self) -> None:
        row = self.ingredients.currentRow()
        if row >= 0:
            self.ingredients.removeRow(row)

    def move_ingredient(self, delta: int) -> None:
        row = self.ingredients.currentRow()
        target = row + delta
        if row < 0 or target < 0 or target >= self.ingredients.rowCount():
            return
        values = [self.ingredients.item(row, col).text() if self.ingredients.item(row, col) else "" for col in range(4)]
        target_values = [self.ingredients.item(target, col).text() if self.ingredients.item(target, col) else "" for col in range(4)]
        for col in range(4):
            self.ingredients.setItem(row, col, QTableWidgetItem(target_values[col]))
            self.ingredients.setItem(target, col, QTableWidgetItem(values[col]))
        self.ingredients.setCurrentCell(target, 2)

    def collect_ingredients(self) -> list[dict]:
        ingredients: list[dict] = []
        for row in range(self.ingredients.rowCount()):
            amount = self._cell(row, 0)
            unit = self._cell(row, 1)
            item = self._cell(row, 2)
            note = self._cell(row, 3)
            if not any([amount, unit, item, note]):
                continue
            ingredient: dict = {}
            if amount:
                try:
                    ingredient["amount"] = float(amount) if "." in amount else int(amount)
                except ValueError:
                    ingredient["amount"] = amount
            else:
                ingredient["amount"] = ""
            if unit:
                ingredient["unit"] = unit
            if item:
                ingredient["item"] = item
            if note:
                ingredient["note"] = note
            ingredients.append(ingredient)
        return ingredients

    def _cell(self, row: int, col: int) -> str:
        item = self.ingredients.item(row, col)
        return item.text().strip() if item else ""

    # ----------------------------- Directions -----------------------------
    def add_direction(self) -> None:
        text = self._direction_dialog("Add Direction")
        if text:
            self.directions.addItem(QListWidgetItem(text))
            self.directions.setCurrentRow(self.directions.count() - 1)

    def edit_direction(self) -> None:
        item = self.directions.currentItem()
        if item:
            self._edit_direction_item(item)

    def _edit_direction_item(self, item: QListWidgetItem) -> None:
        text = self._direction_dialog("Edit Direction", item.text())
        if text:
            item.setText(text)

    def _direction_dialog(self, title: str, initial: str = "") -> str:
        dialog = QDialog(self)
        dialog.setWindowTitle(title)
        dialog.resize(600, 280)
        layout = QVBoxLayout(dialog)
        editor = QTextEdit()
        editor.setPlainText(initial)
        editor.setPlaceholderText("Describe this step…")
        layout.addWidget(editor)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            return editor.toPlainText().strip()
        return ""

    def remove_direction(self) -> None:
        row = self.directions.currentRow()
        if row >= 0:
            self.directions.takeItem(row)

    def move_direction(self, delta: int) -> None:
        row = self.directions.currentRow()
        target = row + delta
        if row < 0 or target < 0 or target >= self.directions.count():
            return
        item = self.directions.takeItem(row)
        self.directions.insertItem(target, item)
        self.directions.setCurrentRow(target)

    def collect_directions(self) -> list[str]:
        return [self.directions.item(i).text().strip() for i in range(self.directions.count()) if self.directions.item(i).text().strip()]

    # ----------------------------- Recipe object -----------------------------
    def build_recipe(self) -> dict:
        title = self.title_edit.text().strip()
        slug = slugify(title)
        return {
            "name": title,
            "url": f"recipes/{slug}.html",
            "ingredients": self.collect_ingredients(),
            "directions": self.collect_directions(),
            **({"subtitle": self.subtitle_edit.text().strip()} if self.subtitle_edit.text().strip() else {}),
        }

    def validate_form(self, show_dialog: bool = True) -> tuple[bool, list[str]]:
        errors: list[str] = []
        title = self.title_edit.text().strip()
        category = self.category_combo.currentText().strip()
        subcategory = self.subcategory_combo.currentText().strip()
        ingredients = self.collect_ingredients()
        directions = self.collect_directions()

        if not title:
            errors.append("Recipe Title is required.")
        if category not in CATEGORIES:
            errors.append("Choose a valid category.")
        if not subcategory:
            errors.append("Sub-Category is required.")
        if not self.image_source or not self.image_source.exists():
            errors.append("A recipe photo is required.")
        if not ingredients:
            errors.append("Add at least one ingredient.")
        elif any(not ingredient.get("item") for ingredient in ingredients):
            errors.append("Every ingredient row must have an Ingredient name.")
        if not directions:
            errors.append("Add at least one direction step.")
        if title and slugify(title) == "recipe":
            errors.append("Recipe Title does not produce a valid recipe slug.")

        if self.project_root and title:
            normalized = normalize_name(title)
            try:
                existing = self._load_all_recipes()
                duplicate = next((r for _c, _s, r in existing if normalize_name(str(r.get("name", ""))) == normalized), None)
                if duplicate:
                    errors.append(f'A recipe named "{title}" already exists.')
                slug = slugify(title)
                duplicate_url = next((r for _c, _s, r in existing if str(r.get("url", "")).casefold() == f"recipes/{slug}.html".casefold()), None)
                if duplicate_url and not duplicate:
                    errors.append(f'The recipe URL slug "{slug}" is already in use.')
            except Exception as exc:
                errors.append(f"Could not read the recipe JSON files: {exc}")
        elif not self.project_root:
            errors.append("Select the TritleKitchen V2 project folder first.")

        ok = not errors
        self.validation_label.setText("✓ Ready to add recipe" if ok else "✕ " + errors[0])
        self.validation_label.setStyleSheet(f"color:{GREEN if ok else RED};")
        if show_dialog:
            if ok:
                QMessageBox.information(self, "Validation Passed", "The recipe is ready to be added to Tritle Kitchen V2.")
            else:
                QMessageBox.warning(self, "Recipe Needs Attention", "\n".join(f"• {e}" for e in errors))
        return ok, errors

    # ----------------------------- Preview / Save -----------------------------
    def _update_preview_header(self) -> None:
        if not hasattr(self, "preview_title"):
            return
        title = self.title_edit.text().strip() or "Recipe Title"
        category = self.category_combo.currentText() if hasattr(self, "category_combo") else "Category"
        subcategory = self.subcategory_combo.currentText().strip() or "Sub-Category"
        self.preview_title.setText(title)
        self.preview_meta.setText(f"{category} / {subcategory}")
        try:
            self.preview_json_box.setPlainText(json.dumps(self.build_recipe(), ensure_ascii=False, indent=2))
        except Exception:
            pass

    def preview_json(self) -> None:
        self._update_preview_header()
        QMessageBox.information(self, "Recipe JSON Preview", self.preview_json_box.toPlainText())

    def _prepare_image(self, target: Path) -> None:
        if not self.image_source:
            raise ValueError("No image selected.")
        source = self.image_source
        suffix = source.suffix.lower()
        if suffix == ".jpg":
            shutil.copy2(source, target)
            return
        if suffix == ".png":
            shutil.copy2(source, target)
            return
        # Convert JPEG variants, WebP, BMP, etc. to JPG using Qt so no Pillow dependency is needed.
        image = QImage(str(source))
        if image.isNull():
            raise ValueError(f"Unable to read image: {source}")
        if not image.save(str(target), "JPG", 94):
            raise ValueError(f"Unable to convert image to JPG: {source}")

    def add_recipe(self) -> None:
        valid, errors = self.validate_form(show_dialog=False)
        if not valid:
            QMessageBox.warning(self, "Recipe Needs Attention", "\n".join(f"• {e}" for e in errors))
            return

        category = self.category_combo.currentText().strip()
        subcategory = self.subcategory_combo.currentText().strip()
        recipe = self.build_recipe()
        json_path = self._category_path(category)
        slug = slugify(recipe["name"])
        image_dir = self.project_root / "assets" / "recipes"
        image_target = image_dir / f"{slug}.jpg"
        if self.image_source and self.image_source.suffix.lower() == ".png":
            image_target = image_dir / f"{slug}.png"
        elif self.image_source and self.image_source.suffix.lower() == ".jpg":
            image_target = image_dir / f"{slug}.jpg"

        if image_target.exists():
            QMessageBox.warning(self, "Image Already Exists", f"The image already exists:\n{image_target}")
            return

        preview_lines = [
            f"Recipe: {recipe['name']}",
            f"Category: {category}",
            f"Sub-Category: {subcategory}",
            f"JSON: {json_path}",
            f"Image: {image_target}",
            "",
            "This will modify the selected category JSON and add the image to assets/recipes.",
        ]
        confirm = QMessageBox.question(
            self,
            "Add Recipe to Tritle Kitchen",
            "\n".join(preview_lines),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return

        try:
            data = read_json(json_path)
            if subcategory not in data:
                data[subcategory] = []
            if not isinstance(data[subcategory], list):
                raise ValueError(f'Sub-category "{subcategory}" is not a recipe list in {json_path.name}.')

            data[subcategory].append(recipe)
            sorted_data = {key: data[key] for key in sorted(data.keys(), key=str.casefold)}
            for key in sorted_data:
                sorted_data[key] = sorted(
                    sorted_data[key],
                    key=lambda r: normalize_name(str(r.get("name", ""))),
                )

            image_dir.mkdir(parents=True, exist_ok=True)
            self._prepare_image(image_target)
            write_json(json_path, sorted_data)
        except Exception as exc:
            # If image creation succeeded but JSON failed, remove only the newly created image.
            try:
                if image_target.exists():
                    image_target.unlink()
            except Exception:
                pass
            QMessageBox.critical(self, "Could Not Add Recipe", str(exc))
            return

        QMessageBox.information(
            self,
            "Recipe Added",
            f"{recipe['name']} was added successfully.\n\nUpdated:\n{json_path}\n{image_target}",
        )
        self.clear_form()
        self._refresh_subcategories()

    def clear_form(self) -> None:
        self.title_edit.clear()
        self.subtitle_edit.clear()
        self.category_combo.setCurrentIndex(0)
        self.subcategory_combo.setCurrentText("")
        self.ingredients.setRowCount(0)
        self.directions.clear()
        self.clear_image()
        self.validation_label.setText("Ready")
        self.validation_label.setStyleSheet(f"color:{MUTED};")
        self._update_preview_header()


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setOrganizationName("TritleKitchen")
    window = RecipeCreator()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
