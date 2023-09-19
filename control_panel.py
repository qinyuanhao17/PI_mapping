import sys
import os
import time
import pythoncom
import nidaqmx
import pi_mapping_ui
import pandas as pd
import numpy as np
import pyqtgraph as pg
from pipython import GCSDevice, pitools
from threading import Thread
from PyQt5.QtGui import QIcon, QPixmap, QCursor, QMouseEvent, QColor, QFont
from PyQt5.QtCore import Qt, pyqtSignal, QPoint, QEvent
from PyQt5.QtWidgets import QWidget, QApplication, QGraphicsDropShadowEffect, QFileDialog, QDesktopWidget, QVBoxLayout

class MyWindow(pi_mapping_ui.Ui_Form, QWidget):
    pi_info_msg = pyqtSignal(str)
    progress_bar_info = pyqtSignal(float)
    def __init__(self):

        super().__init__()

        # init UI
        self.setupUi(self)
        self.ui_width = int(QDesktopWidget().availableGeometry().size().width()*0.5)
        self.ui_height = int(QDesktopWidget().availableGeometry().size().height()*0.55)
        self.resize(self.ui_width, self.ui_height)
        center_pointer = QDesktopWidget().availableGeometry().center()
        x = center_pointer.x()
        y = center_pointer.y()
        old_x, old_y, width, height = self.frameGeometry().getRect()
        self.move(int(x - width / 2), int(y - height / 2))

        # set flag off and widget translucent
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        # set window blur
        self.render_shadow()
        
        # init window button signal
        self.window_btn_signal()

        # init pi contol
        self.pi_init()

        # init signal
        self.pi_signal()
        # Init pi setup info ui
        self.pi_info_ui()
        self.pi_info_msg.connect(self.pi_slot)
    def pi_init(self):
        self.STAGES = ['L-511.44AD00', 'L-511.44AD00', 'NOSTAGE', 'NOSTAGE']
        self.REFMODE = ['FNL', 'FNL']
        self.pidevice = GCSDevice('C-884')
        self.pidevice.ConnectUSB(serialnum='118078756')
        pitools.startup(self.pidevice, stages=self.STAGES,refmodes=self.REFMODE)
        self.pi_info_msg.emit('connected: {}'.format(self.pidevice.qIDN().strip()))
        position_list = list(self.pidevice.qPOS().values())
        position_x = position_list[0]
        position_y = position_list[1]
        self.x_spbx.setValue(position_x)
        self.y_spbx.setValue(position_y)
    def pi_info_ui(self):

        self.pi_msg.setWordWrap(True)  # 自动换行
        self.pi_msg.setAlignment(Qt.AlignTop)  # 靠上

        # 用于存放消息
        self.pi_msg_history = []
    def pi_slot(self, msg):

        self.pi_msg_history.append(msg)
        self.pi_msg.setText("<br>".join(self.pi_msg_history))
        self.pi_msg.resize(700, self.pi_msg.frameSize().height() + 20)
        self.pi_msg.repaint()  # 更新内容，如果不更新可能没有显示新内容  
    def init_nidaq(self):
        self.x_task = nidaqmx.Task()
        self.x_task.ao_channels.add_ao_voltage_chan("cDAQ1Mod1/ao0", min_val=-1.0, max_val=6.0)
        self.y_task = nidaqmx.Task()
        self.y_task.ao_channels.add_ao_voltage_chan("cDAQ1Mod1/ao1", min_val=-1.0, max_val=6.0)

        self.pi_scroll.verticalScrollBar().rangeChanged.connect(
            lambda: self.pi_scroll.verticalScrollBar().setValue(
                self.pi_scroll.verticalScrollBar().maximum()
            )
        )
    def pi_signal(self):
        self.x_move_tbtn.clicked.connect(self.x_moveto)
        self.x_spbx.editingFinished.connect(self.x_moveto)
        self.y_move_tbtn.clicked.connect(self.y_moveto)
        self.y_spbx.editingFinished.connect(self.y_moveto)
        self.velocity_set_tbtn.clicked.connect(self.set_velocity)
        self.velocity_spbx.editingFinished.connect(self.set_velocity)
        #move buttons
        self.y_plus_btn.clicked.connect(self.y_plus)
        self.y_minus_btn.clicked.connect(self.y_minus)
        self.x_plus_btn.clicked.connect(self.x_plus)
        self.x_minus_btn.clicked.connect(self.x_minus)
        self.pi_stp_btn.clicked.connect(self.stop_all)
        self.set_ref_tbtn.clicked.connect(self.set_reference)
        self.home_tbtn.clicked.connect(self.home_to_reference)
        
        # mapping signals
        self.mapping_frame_calc_btn.clicked.connect(self.calc_frames)
        self.mapping_start_btn.clicked.connect(self.mapping_thread)
        self.mapping_interrupt_btn.clicked.connect(self.interrupt_mapping)
        self.mapping_return_btn.clicked.connect(self.return_mapping_origin)

        self.progress_bar_info.connect(self.progress_bar_thread)

    def progress_bar_thread(self,msg):
        self.mapping_progressbar.setValue(int(msg))
    def mapping_thread(self):
        thread = Thread(
            target=self.mapping_start
        )
        thread.start()
    def mapping_start(self):
        pythoncom.CoInitialize()
        start_x = float(self.start_voltage_x.value())/20
        start_y = float(self.start_voltage_y.value())/20
        stop_x = float(self.stop_voltage_x.value())/20
        stop_y = float(self.stop_voltage_y.value())/20
        step_x = float(self.mapping_step_voltage_x.value())/20
        step_y = float(self.mapping_step_voltage_y.value())/20
        intTime = int(self.intTime_spbx.value())
        tot_frame = int(self.frame_spbx.value())
        x_list = np.arange(start_x, stop_x+step_x, step_x)
        y_list = np.arange(start_y, stop_y+step_y, step_y)
        y_list_check_index = list(y_list)
        self.__stopConstant == False
        progress = 0
        with nidaqmx.Task() as read_task, nidaqmx.Task() as write_task:
    
            di = read_task.di_channels.add_di_chan("Dev1/port0/line1")
            do = write_task.do_channels.add_do_chan("Dev1/port0/line0")  
            
            for i in y_list:
                self.y_task.write(i)
                self.y_voltage.setValue(i*20)
                if y_list_check_index.index(i) % 2 == 0:
                    for j in x_list:
                        self.x_task.write(j)
                        self.x_voltage.setValue(i*20)
                        time.sleep(0.5)
                        while True:
                            data = read_task.read()
                            if data == False:
                                break                          
                        write_task.write(True)
                        time.sleep(0.01)
                        write_task.write(False)
                        time.sleep(intTime+1)
                        progress+=1
                        self.progress_bar_info.emit(progress/tot_frame*100)
                elif y_list_check_index.index(i) % 2 != 0:
                    for j in x_list[::-1]:
                        self.x_task.write(j)
                        self.x_voltage.setValue(i*20)
                        time.sleep(0.5)
                        while True:
                            data = read_task.read()
                            if data == False:
                                break                          
                        write_task.write(True)
                        time.sleep(0.01)
                        write_task.write(False)
                        time.sleep(intTime+1)
                        progress+=1
                        self.progress_bar_info.emit(progress/tot_frame*100)
                if self.__stopConstant == True:
                    self.pi_info_msg.emit('Mapping interrupted.')
                    break
            self.pi_info_msg.emit('Mapping finished.')
        pythoncom.CoUninitialize()
    def interrupt_mapping(self):
        self.__stopConstant == True
    def return_mapping_origin(self):
        start_x = float(self.start_voltage_x.value())/20
        start_y = float(self.start_voltage_y.value())/20
        while True:
            x_pos = float(self.x_voltage.value())/20
            step_x = float(self.mapping_step_voltage_x.value())/20
            current_position = x_pos - step_x
            self.x_task.write(current_position)
            self.x_voltage.setValue(current_position*20)
            if current_position - start_x <= 1/20:
                self.x_task.write(start_x)
                self.x_voltage.setValue(start_x*20)
                break
        while True:
            y_pos = float(self.y_voltage.value())/20
            step_y = float(self.mapping_step_voltage_y.value())/20
            current_position = y_pos - step_y
            self.y_task.write(current_position)
            self.y_voltage.setValue(current_position*20)
            if current_position - start_y <= 1/20:
                self.y_task.write(start_y)
                self.y_voltage.setValue(start_y*20)
                break

    def calc_frames(self):
        start_x = float(self.start_voltage_x.value())/20
        start_y = float(self.start_voltage_y.value())/20
        stop_x = float(self.stop_voltage_x.value())/20
        stop_y = float(self.stop_voltage_y.value())/20
        step_x = float(self.mapping_step_voltage_x.value())/20
        step_y = float(self.mapping_step_voltage_x.value())/20
        if (stop_x - start_x) % step_x == 0 and (stop_y -start_y) % step_y == 0:
            frames = ((stop_x - start_x)/step_x + 1) * ((stop_y -start_y)/step_y +1)
            self.frame_spbx.setValue(frames)
    def set_velocity(self):
        velocity = float(self.velocity_spbx.value())
        self.pidevice.VLS(velocity)
        current_velocity = self.pidevice.qVEL()
        self.pi_info_msg.emit('current_velocity'+current_velocity)
    def home_to_reference(self):
        ref_x = self.float(self.refx_spbx.value())
        ref_y = self.float(self.refy_spbx.value())
        self.pidevice.MOV({'1':ref_x, '2':ref_y})
        pitools.waitontarget(self.pidevice)
    def set_reference(self):
        position_list = list(self.pidevice.qPOS().values())
        position_x = position_list[0]
        position_y = position_list[1]
        self.refx_spbx.setValue(position_x)
        self.refy_spbx.setValue(position_y)
    def stop_all(self):
        self.pidevice.STP()
    def y_plus(self):
        position_list = list(self.pidevice.qPOS().values())
        
        position_y = position_list[1]
        
        step = float(self.step_spbx.value())
        target_position = position_y + step
        self.pi_info_msg.emit('current position '+str(target_position))
        self.pidevice.MOV({'2':target_position})
        pitools.waitontarget(self.pidevice)
        self.y_spbx.setValue(position_y)
    def y_minus(self):
        position_list = list(self.pidevice.qPOS().values())
        
        position_y = position_list[1]
        
        step = float(self.step_spbx.value())
        target_position = position_y - step
        self.pi_info_msg.emit('current position '+str(target_position))
        self.pidevice.MOV({'2':target_position})
        pitools.waitontarget(self.pidevice)
        self.y_spbx.setValue(position_y)
    def x_plus(self):
        position_list = list(self.pidevice.qPOS().values())
        
        position_x = position_list[0]
        
        step = float(self.step_spbx.value())
        target_position = position_x + step
        self.pi_info_msg.emit('current position '+str(target_position))
        self.pidevice.MOV({'1':target_position})
        pitools.waitontarget(self.pidevice)
        self.x_spbx.setValue(position_x)
    def x_minus(self):
        position_list = list(self.pidevice.qPOS().values())
        
        position_x = position_list[0]
        
        step = float(self.step_spbx.value())
        target_position = position_x - step
        self.pi_info_msg.emit('current position '+str(target_position))
        self.pidevice.MOV({'1':target_position})
        pitools.waitontarget(self.pidevice)
        self.x_spbx.setValue(position_x)
    def x_moveto(self):
        x_pos = float(self.x_spbx.value())
        self.pidevice.MOV({'1':x_pos})
        pitools.waitontarget(self.pidevice)
        position_list = list(self.pidevice.qPOS().values())
        position_x = position_list[0]
        self.x_spbx.setValue(position_x)
    def y_moveto(self):
        y_pos = float(self.y_spbx.value())
        self.pidevice.MOV({'2':y_pos})
        pitools.waitontarget(self.pidevice)
        position_list = list(self.pidevice.qPOS().values())
        position_y = position_list[1]
        self.y_spbx.setValue(position_y)
    '''Set window ui'''
    def window_btn_signal(self):
        # window button sigmal
        self.close_btn.clicked.connect(self.close)
        self.max_btn.clicked.connect(self.maxornorm)
        self.min_btn.clicked.connect(self.showMinimized)
        
    #create window blur
    def render_shadow(self):
        self.shadow = QGraphicsDropShadowEffect(self)
        self.shadow.setOffset(0, 0)  # 偏移
        self.shadow.setBlurRadius(30)  # 阴影半径
        self.shadow.setColor(QColor(128, 128, 255))  # 阴影颜色
        self.mainwidget.setGraphicsEffect(self.shadow)  # 将设置套用到widget窗口中

    def maxornorm(self):
        if self.isMaximized():
            self.showNormal()
            self.norm_icon = QIcon()
            self.norm_icon.addPixmap(QPixmap(":/my_icons/images/icons/max.svg"), QIcon.Normal, QIcon.Off)
            self.max_btn.setIcon(self.norm_icon)
        else:
            self.showMaximized()
            self.max_icon = QIcon()
            self.max_icon.addPixmap(QPixmap(":/my_icons/images/icons/norm.svg"), QIcon.Normal, QIcon.Off)
            self.max_btn.setIcon(self.max_icon)

    def mousePressEvent(self, event):

        if event.button() == Qt.LeftButton:
            self.m_flag = True
            self.m_Position = QPoint
            self.m_Position = event.globalPos() - self.pos()  # 获取鼠标相对窗口的位置
            event.accept()
            self.setCursor(QCursor(Qt.OpenHandCursor))  # 更改鼠标图标
        
    def mouseMoveEvent(self, QMouseEvent):
        m_position = QPoint
        m_position = QMouseEvent.globalPos() - self.pos()
        width = QDesktopWidget().availableGeometry().size().width()
        height = QDesktopWidget().availableGeometry().size().height()
        if m_position.x() < width*0.7 and m_position.y() < height*0.06:
            self.m_flag = True
            if Qt.LeftButton and self.m_flag:                
                pos_x = int(self.m_Position.x())
                pos_y = int(self.m_Position.y())
                if pos_x < width*0.7 and pos_y < height*0.06:           
                    self.move(QMouseEvent.globalPos() - self.m_Position)  # 更改窗口位置
                    QMouseEvent.accept()

    def mouseReleaseEvent(self, QMouseEvent):
        self.m_flag = False
        self.setCursor(QCursor(Qt.ArrowCursor))
    def closeEvent(self, event):
        while True:
            x_pos = float(self.x_voltage.value())/20
            
            current_position = x_pos - 10/20
            self.x_task.write(current_position)
            self.x_voltage.setValue(current_position*20)
            if current_position <= 10/20:
                self.x_task.write(0)
                self.x_voltage.setValue(0)
                break
        while True:
            y_pos = float(self.y_voltage.value())/20
            
            current_position = y_pos - 10/20
            self.y_task.write(current_position)
            self.y_voltage.setValue(current_position*20)
            if current_position <= 1/20:
                self.y_task.write(0)
                self.y_voltage.setValue(0)
                break
        self.x_task.close()
        self.y_task.close()
    
if __name__ == '__main__':

    app = QApplication(sys.argv)
    w = MyWindow()
    w.show()
    app.exec()
