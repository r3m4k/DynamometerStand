# -*- coding: utf-8 -*-
"""Модуль для работы с графиками pyqtgraph."""

# System imports
from typing import Optional, List, Union

# External imports
import numpy as np
import pyqtgraph as pg
from PyQt5.QtCore import QObject, pyqtSignal

# User imports
from config import config

##########################################################

class PlottingWidget(QObject):
    """Виджет для отображения динамических данных одного датчика.

    Сигналы:
        regionSelected(minX, maxX): испускается, когда пользователь выделил область.
        pointClicked(x, y): испускается при клике на точку данных (если включено).
        viewRangeChanged(minX, maxX, minY, maxY): при изменении видимого диапазона.
    """

    regionSelected = pyqtSignal(float, float)
    pointClicked = pyqtSignal(float, float)
    viewRangeChanged = pyqtSignal(float, float, float, float)

    def __init__(self, plot_widget: pg.PlotWidget):
        super().__init__()

        # -------------------------------------------------------------
        # Проверка типов переданных параметров
        if not isinstance(plot_widget, pg.PlotWidget):
            raise TypeError(f"Ожидается plot_widget: pg.PlotWidget, получен {type(plot_widget)}")
        # -------------------------------------------------------------

        self._plot_widget = plot_widget
        self._curve: pg.PlotDataItem = self._plot_widget.plot()
        self._x_buffer: list[float] = []
        self._y_buffer: list[float] = []

        # Интерактивные элементы
        self._crosshair_v = None
        self._crosshair_h = None
        self._crosshair_label = None
        self._show_crosshair = False
        self._region_item = None
        self._enable_point_click = False

        # Подключение сигналов изменения диапазона
        self._plot_widget.sigRangeChanged.connect(self._on_view_range_changed)

    def configure(self,
                  title: Optional[str] = None,
                  x_label: Optional[str] = None,
                  y_label: Optional[str] = None,
                  background: str = 'w',
                  **curve_kwargs) -> None:
        """Настройка внешнего вида графика и создание кривой."""
        self.clear()    # Отчистим данные перед конфигурацией

        if title:
            self._plot_widget.setTitle(title)
        if x_label:
            self._plot_widget.setLabel('bottom', x_label)
        if y_label:
            self._plot_widget.setLabel('left', y_label)
        self._plot_widget.setBackground(background)

        # Настройки по умолчанию
        self._plot_widget.setMenuEnabled(True)  # контекстное меню по умолчанию
        self._plot_widget.setMouseEnabled(x=True, y=True)
        self._plot_widget.showGrid(x=True, y=True)

        self._curve = self._plot_widget.plot(**curve_kwargs)

    def append_data(self, x_value: float, y_value: float) -> None:
        """Добавляет новую точку данных на график."""
        self._x_buffer.append(x_value)
        self._y_buffer.append(y_value)
        self._curve.setData(self._x_buffer, self._y_buffer)
        self._plot_widget.autoRange()

    # ========== Интерактивные элементы ==========

    def enable_crosshair(self, enable: bool = True):
        """Включает/выключает отображение перекрестия с координатами."""
        if enable and not self._show_crosshair:
            self._show_crosshair = True
            # Создаем вертикальную и горизонтальную линии
            self._crosshair_v = pg.InfiniteLine(angle=90, movable=False, pen=pg.mkPen('r', width=1))
            self._crosshair_h = pg.InfiniteLine(angle=0, movable=False, pen=pg.mkPen('r', width=1))
            self._plot_widget.addItem(self._crosshair_v)
            self._plot_widget.addItem(self._crosshair_h)

            # Текстовое поле для отображения координат
            self._crosshair_label = pg.TextItem(text='', color='k', anchor=(0,1))
            self._plot_widget.addItem(self._crosshair_label)

            # Подключаем событие движения мыши
            self._plot_widget.scene().sigMouseMoved.connect(self._on_mouse_moved)

        elif not enable and self._show_crosshair:
            self._show_crosshair = False
            self._plot_widget.removeItem(self._crosshair_v)
            self._plot_widget.removeItem(self._crosshair_h)
            self._plot_widget.removeItem(self._crosshair_label)
            self._crosshair_v = self._crosshair_h = self._crosshair_label = None
            # Отключаем сигнал
            try:
                self._plot_widget.scene().sigMouseMoved.disconnect(self._on_mouse_moved)
            except:
                pass

    def _on_mouse_moved(self, pos):
        """Обновляет положение перекрестия и текст с координатами."""
        if not self._show_crosshair:
            return
        # Преобразуем координаты сцены в координаты графика
        mouse_point = self._plot_widget.plotItem.vb.mapSceneToView(pos)
        x, y = mouse_point.x(), mouse_point.y()
        self._crosshair_v.setPos(x)
        self._crosshair_h.setPos(y)
        # Обновляем текст (можно отформатировать)
        self._crosshair_label.setText(f'({x:.2f}, {y:.2f})')
        # Позиционируем текст рядом с курсором (например, смещение)
        self._crosshair_label.setPos(x, y)

    def enable_region_selection(self, enable: bool = True):
        """Включает возможность выделения области мышью (LinearRegionItem)."""
        if enable and self._region_item is None:
            self._region_item = pg.LinearRegionItem()
            self._region_item.setZValue(10)
            self._region_item.sigRegionChangeFinished.connect(self._on_region_changed)
            self._plot_widget.addItem(self._region_item)
        elif not enable and self._region_item is not None:
            self._plot_widget.removeItem(self._region_item)
            self._region_item = None

    def _on_region_changed(self):
        """Обрабатывает изменение выделенной области."""
        if self._region_item is not None:
            minX, maxX = self._region_item.getRegion()
            self.regionSelected.emit(minX, maxX)

    def enable_point_click(self, enable: bool = True):
        """Включает возможность клика по точкам данных (сигнал pointClicked)."""
        self._enable_point_click = enable
        if enable:
            # Подключаем событие клика мыши на кривой
            if self._curve is not None:
                self._curve.sigClicked.connect(self._on_curve_clicked)
        else:
            if self._curve is not None:
                try:
                    self._curve.sigClicked.disconnect(self._on_curve_clicked)
                except:
                    pass

    def _on_curve_clicked(self, curve, points):
        """Обрабатывает клик по точке данных."""
        if points:
            # Берём первую точку в выделении (клик может дать несколько)
            point = points[0]
            x = point.pos().x()
            y = point.pos().y()
            self.pointClicked.emit(x, y)

    def _on_view_range_changed(self, vb, ranges):
        """Передаёт изменение видимого диапазона."""
        x_range = ranges[0]
        y_range = ranges[1]
        self.viewRangeChanged.emit(x_range[0], x_range[1], y_range[0], y_range[1])

    # ========== Дополнительные методы управления ==========
    def clear(self) -> None:
        """Очищает данные."""
        self._x_buffer.clear()
        self._y_buffer.clear()
        self._curve.clear()

    def auto_range(self) -> None:
        self._plot_widget.autoRange()