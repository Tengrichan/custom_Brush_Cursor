from PyQt5.QtWidgets import (
        QLabel,
        QWidget,
        QMessageBox,
        QCheckBox,
        QToolButton,
        QMdiArea,
        QListWidget,
        QPushButton,
        QVBoxLayout,
        QHBoxLayout,
        QGridLayout,
        QSlider,
        QFileDialog,
        QPlainTextEdit,
        QOpenGLWidget,
        QMdiSubWindow,
        QListView,
        QAbstractItemView,
        QScrollArea,
        QLayoutItem)
        
from krita import (
        Krita,
        Extension,
        DockWidget,
        DockWidgetFactory,
        DockWidgetFactoryBase)

from PyQt5.QtCore import (
        Qt,
        QDir,
        QEvent,
        QPoint,
        QSize,
        QSettings,
        QItemSelectionModel,
        QTimer,
        pyqtSignal,
        QCoreApplication)

from PyQt5.QtGui import (
        QColor,
        QPainter,
        QPixmap,
        QPalette,
        QCursor,
        QTransform,
        QMouseEvent,
        QTextCursor,
        QStandardItemModel,
        QStandardItem,
        QIcon,
        QTabletEvent)
  

import os
import shutil
import stat
import math
import random

from pathlib import Path #module to handle paths

def findQMdiArea():
    q_window = Krita.instance().activeWindow().qwindow() #Return a handle to the QMainWindow widget. This is useful to e.g. parent dialog boxes and message box
    MdiArea = q_window.findChild(QMdiArea)    

    return MdiArea    #return with MdiArea 

    
 #check if there is an active window --> check the active view and with that document/canvas available 
def isCanvasReady():
    """    
    window = Krita.instance().activeWindow()
    if window:
        views = window.views()
        return len(views) > 0
    return False   
    """
    app = Krita.instance()
    #Is there an active window?
    window = app.activeWindow()
    if not window:
        return False
        
    # Does that window have an active view?
    view = window.activeView()
    if not view:
        return False
        
    #Does that view have a document attached?
    doc = view.document()
    if not doc:
        return False
        
    return True

		
class DebugWindow(QPlainTextEdit):
    
    def __init__(self,**kwargs):
        super().__init__(**kwargs)
	
    def append_to_end(self, text):
        self.moveCursor(QTextCursor.End)
        self.insertPlainText(text)
       
 
class BrushToggledONEvent(QEvent):
    EventType = QEvent.registerEventType()  # Register a new event type
    
    def __init__(self):
        super().__init__(BrushToggledONEvent.EventType)  # Set the event type
        
class BrushToggledOFFEvent(QEvent):
    EventType = QEvent.registerEventType()  # Register a new event type
    
    def __init__(self):
        super().__init__(BrushToggledOFFEvent.EventType)  # Set the event type
        
        
#extension singleton to synchronize the UI settings across multiple windows open
class DockerUISettingsManager(Extension):
    instance = None
    # This signal sends the key name and the new value
    syncSignal = pyqtSignal(str, object)

    def __init__(self,parent):
        super().__init__(parent)
        # Store a static reference so the Docker can find it
        DockerUISettingsManager.instance = self

    def setup(self):
        pass

    def createActions(self, window):
        pass

            
class customBrushCursorDocker(DockWidget):

    def __init__(self):
        super().__init__()
        self.firstRun = True
        self.setWindowTitle("Custom Brush Cursor")
        
        #directory stuff
        self.directory_plugin = str( os.path.dirname( os.path.realpath( __file__ ) ) )
        self.directory_customCursorImage = str("")
        
        #cursor related stuff
        self.selected_label = None
        self.pixmap = QPixmap()    #cursor pixmap
        self.opacity = 0    #variable to keep track of opacity
        self.rotation = 0	#variable to keep track of rotation
        self.customCursor = QCursor()        #the changing version of cursor
        self.staticCustomCursor = QCursor() #an original version of custom cursor which will be used for opacity and scale as a basis
        self.isCustomCursorApplied = False

        #settings related stuff
        self.loadedSetting_selectedIndex = -1    #variable to keep track of the loaded selected index of QListView, by default it's -1
        self.filePathRole = Qt.UserRole    #simple vars used as custom roles for items
        self.fileNameRole = Qt.UserRole + 1
        
        # Create the timer
        self.saveTimer = QTimer()
        self.saveTimer.setSingleShot(True)  # Only fire once per start
        self.saveTimer.setInterval(500)     # Wait 500ms (0.5 seconds)
        self.saveTimer.timeout.connect(self.saveSettings)         # Connect the timer's finish line to actual save function
        
        #DEBUG window related		
        self.dbgWindow = DebugWindow()
        #self.dbgWindow.show()
        
        # Connect to the singleton Extension's signal
        # We use a helper to find the manager instance
        self.manager = DockerUISettingsManager.instance
        self.manager.syncSignal.connect(self.update_ui_from_sync)

        # Define brush tools
        self.brush_tools = ["KritaShape/KisToolBrush", "KritaShape/KisToolMultiBrush", "KritaShape/KisToolLazyBrush", "KritaShape/KisToolDyna"]
        
        #GUI init
        self.initGUI()

        self.create_directory()    #create directory for the images if it doesn't exist already
        self.initIconView_list()    #initialize iconView list based on files found in folder

        #load in settings to check whether runOnStartup is true or false
        #the logic is done here so the variables get a value in time for checks 
        self.loadedSetting_selectedIndex = self.loadSettings()    #roundabout way to load in settings because the method returns with an int but the rest of the variables are assigned a value as well
        
        self.setup()
        
    
    
    def update_ui_from_sync(self, key, value):
        # We block signals so we don't trigger an infinite loop
        self.blockSignals(True)
        if key == "Opacity":
            self.sliderforOpacity.setValue(int(value))
        elif key == "Scale":
            self.sliderforScale.setValue(int(value))
        elif key == "Rotation":
            self.sliderforRotation.setValue(int(value))
        elif key == "runOnStartupCheckbox":
            self.runOnStartup.setChecked(bool(value))
        elif key == "centeredIconCheckbox":
            self.centeredIcon.setChecked(bool(value))
        elif key == "linuxArtistModeFixCheckbox":
            self.linuxArtistModeFixCheckbox.setChecked(bool(value))
        elif key == "SelectedIcon":
            #selected_indices = self.iconView.selectionModel().selectedIndexes()
            #row_to_save = selected_indices[0].row()
            index = self.iconView.model().index(int(value), 0)
            self.iconView.setCurrentIndex(index)
            self.on_icon_clicked(index)
            # ... update other widgets ...
            self.blockSignals(False)    
    
    
    #Timer function to trigger save of settings 
    #it will be called when any of the plugin settings are changed so it needs to be connected to the settings 
    def triggerSave(self):
        """Restarts the timer every time it's called."""
        self.saveTimer.start()


    #get the window the plugin belongs to
    def get_plugins_window(self):
        """Finds the specific MainWindow this Docker is sitting in."""
        return self.window()  # QWidget method that returns the top-level window


    #scales the picture to size and returns with a pixmap
    #arg pixmap,scaleValue
    #return QPixmap
    def pixmapScale(self,pixmap,scaleValue):
        local_pixmap = pixmap
        if (scaleValue < -1):
            if not ( int(pixmap.height()/abs(scaleValue)) == 256):
                scaled_piximage = pixmap.scaled( int(pixmap.width()/abs(scaleValue) ), int(pixmap.height()/abs(scaleValue)) )
                local_pixmap = scaled_piximage
            else:
                scaled_piximage = pixmap.scaled( int(pixmap.width()/abs(scaleValue)), 256 )
                local_pixmap = scaled_piximage
        elif (scaleValue > 1):
            if not ( int(pixmap.height()*scaleValue) == 256):
                scaled_piximage = pixmap.scaled( int(pixmap.width()*scaleValue ), int(pixmap.height()*scaleValue ))
                local_pixmap = scaled_piximage
            else:
                scaled_piximage = pixmap.scaled( int(pixmap.width()*scaleValue), 256 )
                local_pixmap = scaled_piximage
        else: #in case the value is -1,0,1
            local_pixmap = pixmap

        return local_pixmap

    #changes the opacity of the given pixmap with opacity
    #arg pixmap,opacity
    #return QPixmap
    def changeOpacity(self,pixmap,opacity):     
        new_pixmap = QPixmap(pixmap.size() )
        new_pixmap.fill(QColor(0, 0, 0, 0))
        
        painter = QPainter(new_pixmap)
        painter.setOpacity(opacity)
        painter.drawPixmap(0,0, pixmap) #draws a pixmap at (x,y) ; (x,y) specifies top-left origin ; default is (0,0)
        painter.end()
        return new_pixmap
       
    #calculates the new hotspot after the rotation
    #arg scaled_pixmap,transformed_pixmap,rotation in degrees
    #return an (int,int)  tuple
    def calculateCursorHotspot(self,scaled_pixmap,transformed_pixmap,rotation):

        pixmap_width = scaled_pixmap.width()    #get the scaled pixmap width for calculation
        pixmap_height = scaled_pixmap.height()   #get the scaled pixmap height for calculation
        
        #4 sections depending on the rotation value in degrees
        #0-90 --> x:constant = 1 y: changes
        #91 - 180 --> x:changes y:constant = 1
        #181 - 270 --> x: constant = bounding box width - 1 y:changes
        #271 - 360 --> x:changes y:constant = bounding box height  - 1
        
        if (rotation > 0 and rotation <= 90):
           angle_rad = math.radians(rotation)    #rotation degrees translated to radians
           rounded_radianValue= round(angle_rad,10)    #round the radian value down  to 10 decimals

           float_tempY = math.cos(rounded_radianValue) * pixmap_height    #get result in float type
           fractional_part, integer_part = math.modf(float_tempY)    #get the two part of the floating number 
           result_Y = 0
           if (fractional_part < 0.5 ):    #if fractional part is less than 0.5 round down the floating number 
               result_Y = int(math.cos(rounded_radianValue) * pixmap_height)
           else:    #otherwise round it up so add + 1 to it because int()  type casting returns only the integer part  thus rounds it down regardless 
               result_Y = int(math.cos(rounded_radianValue) * pixmap_height) + 1
             
           result_X = 1  
        elif (rotation > 90 and rotation <= 180):
           adjustedDegree = rotation - 90    #we adjust the degree as if it was doine in a 0-90 section
           angle_rad = math.radians(adjustedDegree)
           rounded_radianValue= round(angle_rad,10)    #round the radian value down  to 10 decimals
           
           float_tempX = math.sin(rounded_radianValue) * pixmap_width
           fractional_part, integer_part = math.modf(float_tempX)
           result_X = 0
           if (fractional_part < 0.5 ):    #if fractiona part is less than 0.5 round down the floating number 
               result_X = int(math.sin(rounded_radianValue) * pixmap_width)
           else:    #otherwise round it up so add + 1 to it because int()  type casting returns only the integer part 
               result_X = int(math.sin(rounded_radianValue) * pixmap_width) + 1
            
           result_Y = 1  
        elif (rotation > 180 and rotation <= 270):
            adjustedDegree = rotation - 180    #we adjust the degree as if it was doine in a 0-90 section
            angle_rad = math.radians(adjustedDegree)
            rounded_radianValue= round(angle_rad,10)    #round the radian value down  to 10 decimals
            
            float_tempY = math.sin(rounded_radianValue) * pixmap_width    #get result in float type
            fractional_part, integer_part = math.modf(float_tempY)    #get the two part of the floating number 
            result_Y = 0
            if (fractional_part < 0.5 ):    #if fractional part is less than 0.5 round down the floating number 
                result_Y = int(math.sin(rounded_radianValue) * pixmap_width)
            else:    #otherwise round it up so add + 1 to it because int()  type casting returns only the integer part 
                result_Y = int(math.sin(rounded_radianValue) * pixmap_width) + 1
               
            result_X = transformed_pixmap.width() - 1    #the X coordinate is gonna be the bounding rectangle's width - 1 adjusted because of the brush picture  
        elif (rotation > 270 and rotation < 360):
            adjustedDegree = rotation - 270    #we adjust the degree as if it was doine in a 0-90 section
            angle_rad = math.radians(adjustedDegree)
            rounded_radianValue= round(angle_rad,10)    #round the radian value down  to 10 decimals
            
            float_tempY = math.cos(rounded_radianValue) * pixmap_height    #get result in float type
            fractional_part, integer_part = math.modf(float_tempY)    #get the two part of the floating number 
            result_X = 0
            if (fractional_part < 0.5 ):    #if fractional part is less than 0.5 round down the floating number 
                result_X = int(math.cos(rounded_radianValue) * pixmap_height)
            else:    #otherwise round it up so add + 1 to it because int()  type casting returns only the integer part 
                result_X = int(math.cos(rounded_radianValue) * pixmap_height) + 1
 
            result_Y = transformed_pixmap.height() - 1
        elif (rotation == 360 or rotation == 0):    #no rotation is done 
            result_X = 1
            result_Y = pixmap_height - 1

        return (result_X,result_Y)

    #creates the custom cursor
    # first we scale the pixmap,change its opacity then  rotate around Z axis 
    #arg pixmap,scale,opacity,rotation,crosshair_bool,linuxFIX_bool
    #return QCursor
    def createCustomCursor(self,pixmap,scale,opacity,rotation,crosshair,linuxArtistModeFix):       
       
        scaled_pixmap = self.pixmapScale(pixmap,scale)      #scale the pixmap with input scale value 
        scaled_pixmap = self.changeOpacity(scaled_pixmap,opacity)       #change the opacity of the already scaled pixmap with opacity
               
        transform = QTransform()
        axis = Qt.ZAxis
        transform.rotate(rotation,axis)    # a, axis, distanceToPlane - a = degrees , axis , distancetoPlane = distance from the screen
        transformed_pixmap = scaled_pixmap.transformed(transform)    #this rotates around Z axis
        
        #tuple containing the new (X,Y) values for cursor hotspot
        newhotspot = self.calculateCursorHotspot(scaled_pixmap,transformed_pixmap,rotation)          
        #check whether the orientation of the cursor icon is centered like a crosshair or not
        #if it's centered then use a different offset
        if linuxArtistModeFix:
            qCursor = QCursor(scaled_pixmap,0,-int(scaled_pixmap.height()/2) + 1 )
            if crosshair:
                qCursor = QCursor(scaled_pixmap,int(scaled_pixmap.width()/4),int(scaled_pixmap.height()/4) + 1)
                # qCursor = QCursor(scaled_pixmap,int(int(scaled_pixmap.height())*1.5),0)
            # else:
                # qCursor = QCursor(transformed_pixmap,newhotspot[0],-newhotspot[1])     #create a cursor object from scaledImage and set its coordinates 
        else:
            if crosshair:
                qCursor = QCursor(scaled_pixmap,int(scaled_pixmap.width()/2),int(scaled_pixmap.height()/2) + 1 )
            else:
                #qCursor = QCursor(transformed_pixmap,1,transformed_pixmap.height() - 1)     #create a cursor object from scaledImage and set its coordinates X=0 and Y=move the image up by its height because its orientation
                qCursor = QCursor(transformed_pixmap,newhotspot[0],newhotspot[1])     #create a cursor object from scaledImage and set its coordinates 
        return  qCursor	
    
    def initGUI(self):
        
        self.mainWidget = QWidget(self)
        self.setWidget(self.mainWidget)
        layout = QVBoxLayout(self.mainWidget)
        layout.setContentsMargins(4, 4, 4, 4)  # Reduce padding for compactness
        layout.setSpacing(4)  # Tighter spacing
        self.mainWidget.setMinimumWidth(100)


        # Toggle button
        self.buttonWidget = QWidget(self.mainWidget)
        buttonLayout = QVBoxLayout(self.buttonWidget)
        self.buttonStatus = QPushButton("Activate", self)
        self.buttonStatus.setCheckable(True)
        self.buttonStatus.toggled.connect(self.toggleState)
        buttonLayout.addWidget(self.buttonStatus, alignment=Qt.AlignTop | Qt.AlignHCenter)
        layout.addWidget(self.buttonWidget)

        # Options widget
        self.optionsWidget = QWidget(self.mainWidget)
        optionsLayout = QVBoxLayout(self.optionsWidget)
        optionsLayout.setSpacing(3)  # Compact options

        # Open file button
        self.open_button = QPushButton("Open image file...")
        self.open_button.clicked.connect(self.open_file_dialog)
        optionsLayout.addWidget(self.open_button)

        # Opacity controls
        self.labelforOpacity = QLabel("Opacity: 50%")
        self.sliderforOpacity = QSlider(Qt.Horizontal)
        self.sliderforOpacity.setRange(0, 100)
        self.sliderforOpacity.setValue(50)
        self.sliderforOpacity.valueChanged.connect(self.update_cursorOpacity)
        self.sliderforOpacity.valueChanged.connect(lambda val: self.manager.syncSignal.emit("Opacity",val))    #when slider value changes send out a signal to Extension so other dockers can be updated
        optionsLayout.addWidget(self.labelforOpacity)
        optionsLayout.addWidget(self.sliderforOpacity)

        # Scale controls
        self.labelforScale = QLabel("Scale: 0")
        self.sliderforScale = QSlider(Qt.Horizontal)
        self.sliderforScale.setRange(-10, 10)
        self.sliderforScale.setSingleStep(1)
        self.sliderforScale.setPageStep(1)
        self.sliderforScale.setValue(0)
        self.sliderforScale.valueChanged.connect(self.update_cursorScale)
        self.sliderforScale.valueChanged.connect(lambda val: self.manager.syncSignal.emit("Scale",val))    #when slider value changes send out a signal to Extension so other dockers can be updated
        optionsLayout.addWidget(self.labelforScale)
        optionsLayout.addWidget(self.sliderforScale)

        # Size labels
        self.labelforWidth = QLabel("Width: -")
        self.labelforHeight = QLabel("Height: -")
        # Create a horizontal layout for width and height labels
        labelRowLayout = QHBoxLayout()
        labelRowLayout.addWidget(self.labelforWidth)
        labelRowLayout.addSpacing(15)  # roughly a 'tab' size of spacing
        labelRowLayout.addWidget(self.labelforHeight)

        # Add this horizontal layout to main optionsLayout
        optionsLayout.addLayout(labelRowLayout)

        # Rotation controls
        self.labelforRotation = QLabel("Rotation: 0°")
        self.sliderforRotation = QSlider(Qt.Horizontal)
        self.sliderforRotation.setRange(0, 360)
        self.sliderforRotation.setValue(0)
        self.sliderforRotation.valueChanged.connect(self.update_cursorRotation)
        self.sliderforRotation.valueChanged.connect(lambda val: self.manager.syncSignal.emit("Rotation",val))    #when slider value changes send out a signal to Extension so other dockers can be updated
        optionsLayout.addWidget(self.labelforRotation)
        optionsLayout.addWidget(self.sliderforRotation)

        # Checkboxes
        self.runOnStartup = QCheckBox("Run on startup")
        self.runOnStartup.stateChanged.connect(lambda checked: self.manager.syncSignal.emit("runOnStartupCheckbox",checked))    #when checkbox state changes send out a signal to Extension so other dockers can be updated
        
        self.centeredIcon = QCheckBox("Centered cursor icon")
        self.centeredIcon.stateChanged.connect(self.centerHotspot)
        self.centeredIcon.stateChanged.connect(lambda checked: self.manager.syncSignal.emit("centeredIconCheckbox",checked))    #whencheckbox state changes send out a signal to Extension so other dockers can be updated
        
        self.linuxArtistModeFixCheckbox = QCheckBox("(For Linux) Artist mode fix")
        self.linuxArtistModeFixCheckbox.stateChanged.connect(self.linuxArtistModeFix)
        self.linuxArtistModeFixCheckbox.stateChanged.connect(lambda checked: self.manager.syncSignal.emit("linuxArtistModeFixCheckbox",checked))    #when checkbox state changes send out a signal to Extension so other dockers can be updated
        
        optionsLayout.addWidget(self.runOnStartup, alignment=Qt.AlignTop | Qt.AlignHCenter)
        optionsLayout.addWidget(self.centeredIcon, alignment=Qt.AlignTop | Qt.AlignHCenter)
        optionsLayout.addWidget(self.linuxArtistModeFixCheckbox, alignment=Qt.AlignTop | Qt.AlignHCenter)
      
        layout.addWidget(self.optionsWidget)
        
        # Icon view (replaced QListWidget)
        self.iconView = QListView(self.mainWidget)
        self.iconView.setViewMode(QListView.IconMode)    #set the view mode to IconMode 
        self.iconView.setSelectionMode(QAbstractItemView.SingleSelection)    #set selection mode to Single select only
        self.iconView.setResizeMode(QListView.Adjust)    #behaviour when a resize occurs -> "If this property is Adjust , the items will be laid out again when the view is resized"
        self.iconView.setMovement(QListView.Static)    #property that determines whether the items can be moved freely , Static -> no movement at all
        self.iconView.setSpacing(5)    #padding around the icons , "This property is the size of the empty space that is padded around an item in the layout"
        self.iconView.setIconSize(QSize(32, 32))  # Initial size of the icons
        self.iconView.setMinimumHeight(40)    #set the minimum height of iconview so it will show at least one row of icons at all times
        self.iconView.setGridSize(QSize(37, 37))  # Icon + spacing
        #self.iconView.setFlow(QListView.LeftToRight)
        #self.iconView.setWrapping(True)
        self.iconView.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)    #set dynamic scrollbars based on size
        self.iconView.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.iconView.setEditTriggers(QAbstractItemView.NoEditTriggers)    #remove the ability to edit the icons and related part in any way
        self.iconView.setStyleSheet("QListView::item:selected { border: 1px solid rgba(100, 149, 237, 1); background: rgba(100, 149, 237, 0.2); }")    #use "cornflowerblue" as highlight colour for border and background colour
        self.iconView.clicked.connect(self.on_icon_clicked)  # Add click handler 
        self.iconView.clicked.connect(lambda: self.manager.syncSignal.emit("SelectedIcon" , self.iconView.currentIndex().row())) #when iconView icon changes send out a signal to Extension so other dockers can be updated

        layout.addWidget(self.iconView, stretch=1)    #allow iconView to expand

        # Hide options and iconView by default
        self.optionsWidget.hide()
        self.iconView.hide() 
        
    def adjustIconSize(self):
        viewWidth = self.iconView.viewport().width()    #get current viewport width
        viewHeight = self.iconView.viewport().height()   ##get current viewport height
        spacing = self.iconView.spacing()    #get spacing value
        margins = self.iconView.contentsMargins()    #get margins value if any
        totalMargin = margins.left() + margins.right()    #calculate total margin
        #iconWidth = max(32, min(150, viewWidth // 3 - self.iconView.spacing() * 2)) 
        #iconWidth = max(32, min(150, (viewWidth - totalMargin - spacing * 5) // 4))
        #iconWidth = max(32, min(150, viewWidth // 4))

        # Calculate icon size based on height
        iconHeight = max(32, min(150, viewHeight // 4))  
    
        
        self.iconView.setIconSize(QSize(iconHeight, iconHeight))    #set iconsize with new value
        self.iconView.setGridSize(QSize(iconHeight + spacing , iconHeight + spacing ))    #set gridszie based on iconHeight
        self.iconView.viewport().update()  # Force redraw
        
    #overwrite resizeEvent for iconView to automatically call adjustIconSize()    
    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.iconView.isVisible():
            self.adjustIconSize()
            
    #Krita's writeSetting generally expects strings or basic types
    #saves the state of the sliders and checkboxes into Krita's internal  "kritarc" file
    #arg
    #return 
    def saveSettings(self):        
        """Save the current states using Krita's internal config."""
        # Group name helps organize the settings inside the kritarc file
        group = "customBrushCursorDocker"
        app = Krita.instance()
        
        # Save Sliders
        app.writeSetting(group, "Opacity", str(self.sliderforOpacity.value()))
        app.writeSetting(group, "Scale", str(self.sliderforScale.value()))
        app.writeSetting(group, "Rotation", str(self.sliderforRotation.value()))

        # Save Checkboxes (True/False are stored as strings "true"/"false")
        app.writeSetting(group,"Checkbox_runOnStartup", str(self.runOnStartup.isChecked()))
        app.writeSetting(group, "Checkbox_CenteredCursorIcon", str(self.centeredIcon.isChecked()))
        app.writeSetting(group, "Checkbox_ArtistModeFIX", str(self.linuxArtistModeFixCheckbox.isChecked()))

        # Save QListView selection
        selected_indices = self.iconView.selectionModel().selectedIndexes()
        row_to_save = selected_indices[0].row()
        if selected_indices:
             app.writeSetting(group, "SelectedIcon", str(row_to_save))    #get the list's first entry and save its row attribute
        else:
             app.writeSetting(group, "SelectedIcon", str(-1))               # No selection
       
       
    #when the program is closing and the timer is still running for save settings... stop the timer -> save the settings immediately   
    def on_closing(self):
        if self.saveTimer.isActive():
            self.saveTimer.stop()
            self.saveSettings()    #Force the save now   
            
            
    #loads saved settings 
    #arg
    #return selected_index which is used to create the cursor        
    def loadSettings(self):
        group = "customBrushCursorDocker"
        app = Krita.instance()

       # readSetting(group, key, defaultValue)
       
       # Load Opacity slider state (default to  50 )
        opacity = int(app.readSetting(group, "Opacity", "50"))
        self.sliderforOpacity.setValue(opacity)

        # Load Scale slider state (default to  0 )
        scale = int(app.readSetting(group, "Scale", "0"))
        self.sliderforScale.setValue(scale)
        
        # Load Opacity slider state (default to  0 )
        rotation = int(app.readSetting(group, "Rotation", "0"))
        self.sliderforRotation.setValue(rotation)
        
        # Load Checkbox: Run On Startup state (default to False if not found)
        runOnStartup_val = app.readSetting(group, "Checkbox_runOnStartup", "false").lower() == "true"
        self.runOnStartup.setChecked(runOnStartup_val)        
        
        # Load Checkbox: Centered Cursor Icon state (default to False if not found)
        is_centered = app.readSetting(group, "Checkbox_CenteredCursorIcon", "false").lower() == "true"
        self.centeredIcon.setChecked(is_centered)
        
        # Load Checkbox: Artist mode fix(For Linux) state (default to False if not found)
        artist_mode_fix = app.readSetting(group,"Checkbox_ArtistModeFIX","false").lower() == "true"
        self.linuxArtistModeFixCheckbox.setChecked(artist_mode_fix)
        
        # Load selected index for QListView (if no saved setting is found -1 --> set the 1st item as selected icon)
        selected_index = int(app.readSetting(group,"SelectedIcon", "-1"))
        
        if selected_index != -1:
            self.iconView.setCurrentIndex(self.iconView.model().index(selected_index, 0))    #(row,coloumn) 
        else:
            self.iconView.setCurrentIndex(self.iconView.model().index(0, 0))    #(row,coloumn) == 0,0 so select the first icon in the model
        
        return selected_index
    
    

    def setup(self):
        # Get the notifier instance
        self.notifier = Krita.instance().notifier()
    
        # Connect the viewCreated  SIGNAL to function
        self.notifier.viewCreated.connect(self.on_view_created)

    #when a view is created --> wait a little bit for Krita to set up its internal variables --> call the next function
    def on_view_created(self):
        QTimer.singleShot(100,self.delayed_check)

    #check if an active document is open or not because a document can exist without an available view/Canvas
    def delayed_check(self):
        if (self.firstRun):  # if it's the first run of the program 
            if (isCanvasReady() and self.runOnStartup.isChecked()):    #canvas is available so we opened a document AND run on startup checkbox was checked --> manually toggle the button so as if it was clicked   
                self.firstRun = False    #flip the firstRun bool so when a new view is created the above code won't run again

                self.sliderforOpacity.valueChanged.connect(self.triggerSave)    #call the timer and wait 1 second to save the value
                self.sliderforScale.valueChanged.connect(self.triggerSave)    #call the timer and wait 1 second to save the value
                self.sliderforRotation.valueChanged.connect(self.triggerSave)    #call the timer and wait 1 second to save the value
                self.iconView.selectionModel().selectionChanged.connect(lambda: self.saveSettings())    #set up icon selection change  SIGNAL  --> save the settings 
            
                #set to run the saveSettings method when the checkbox state changed SIGNAL is fired
                self.runOnStartup.stateChanged.connect(self.saveSettings)    #When the checkbox changes its value save settings
                self.centeredIcon.stateChanged.connect(self.saveSettings)    #When the checkbox changes its value save settings
                self.linuxArtistModeFixCheckbox.stateChanged.connect(self.saveSettings)    #When the checkbox changes its value save settings
                
                self.buttonStatus.toggle()    #toggle the button manually via code
            elif (isCanvasReady()):    #if the runOnStartup was not checked but a canvas is available -- > connect the SIGNAL-SLOT connections for UI elements but only on the first run
                self.firstRun = False    #flip the firstRun bool so when a new view is created the above code won't run again

                self.sliderforOpacity.valueChanged.connect(self.triggerSave)    #call the timer and wait 1 second to save the value
                self.sliderforScale.valueChanged.connect(self.triggerSave)    #call the timer and wait 1 second to save the value
                self.sliderforRotation.valueChanged.connect(self.triggerSave)    #call the timer and wait 1 second to save the value
                self.iconView.selectionModel().selectionChanged.connect(lambda: self.saveSettings())    #set up icon selection change  SIGNAL  --> save the settings 
            
                #set to run the saveSettings method when the checkbox state changed SIGNAL is  fired
                self.runOnStartup.stateChanged.connect(self.saveSettings)    #When the checkbox changes its value save settings
                self.centeredIcon.stateChanged.connect(self.saveSettings)    #When the checkbox changes its value save settings
                self.linuxArtistModeFixCheckbox.stateChanged.connect(self.saveSettings)    #When the checkbox changes its value save settings
            else:    #if  there is no available canvas on the first run don't do anything but wait 
               pass
 
            
    def hook_core_app(self):
        """ add hook to core application. """
        if (isCanvasReady()):
            QMdiArea = findQMdiArea()    #get current QMainWindow's - QMdiArea widget

            #connect checkBrushTool  to the brush tool SIGNALs
            q_win = Krita.instance().activeWindow().qwindow()
            KritaShape_KisToolBrush = q_win.findChild(QToolButton,"KritaShape/KisToolBrush")
            KritaShape_KisToolMultiBrush = q_win.findChild(QToolButton,"KritaShape/KisToolMultiBrush")
            KritaShape_KisToolLazyBrush = q_win.findChild(QToolButton,"KritaShape/KisToolLazyBrush")
            KritaShape_KisToolDynamicBrush = q_win.findChild(QToolButton,"KritaShape/KisToolDyna")
            KritaShape_KisToolBrush.toggled.connect(self.checkBrushTool)
            KritaShape_KisToolMultiBrush.toggled.connect(self.checkBrushTool)
            KritaShape_KisToolLazyBrush.toggled.connect(self.checkBrushTool)
            KritaShape_KisToolDynamicBrush.toggled.connect(self.checkBrushTool)
            
            QMdiArea.installEventFilter(self)    #install the eventFilter on this object 
            self.iconView.viewport().installEventFilter(self)    #install the eventFilter on this object 
            
            self.optionsWidget.show()    #show optionsWidget
            self.iconView.show()  # show iconView 

    def release_core_app(self):
        """ remove hook from core application. """
        QMdiArea = findQMdiArea()    #get current QMainWindow's - QMdiArea widget
        #disconnect checkBrushTool  from the brush tool SIGNALs
        q_win = Krita.instance().activeWindow().qwindow()
        KritaShape_KisToolBrush = q_win.findChild(QToolButton,"KritaShape/KisToolBrush")
        KritaShape_KisToolMultiBrush = q_win.findChild(QToolButton,"KritaShape/KisToolMultiBrush")
        KritaShape_KisToolLazyBrush = q_win.findChild(QToolButton,"KritaShape/KisToolLazyBrush")
        KritaShape_KisToolDynamicBrush = q_win.findChild(QToolButton,"KritaShape/KisToolDyna")
        KritaShape_KisToolBrush.toggled.disconnect(self.checkBrushTool)
        KritaShape_KisToolMultiBrush.toggled.disconnect(self.checkBrushTool)
        KritaShape_KisToolLazyBrush.toggled.disconnect(self.checkBrushTool)
        KritaShape_KisToolDynamicBrush.toggled.disconnect(self.checkBrushTool)
            
        QMdiArea.removeEventFilter(self)    #remove eventFilter from this object
        self.iconView.viewport().removeEventFilter(self)    #remove eventFilter from this object
        self.optionsWidget.hide()    #hide optionsWidget
        self.iconView.hide()  # hide iconView 


    #main plugin ON/OFF button
    #arg button's toggled value
    #sets up the SIGNAL-SLOT relations for UI elements to automatically save when values are changed
    def toggleState(self, checked):
        #If the button is checked == True
        if checked:
            self.buttonStatus.setText('Deactivate')    #set the text on the button to "Deactivate"
            self.createCustomCursorFromModel_Item()    #then we create the custom cursor based on the loaded settings
            self.hook_core_app()   #install eventFilters then show the widgets
        else:
            self.buttonStatus.setText('Activate')    #set the text on the button to "Activate"
            self.release_core_app()     #then disconnect all the SIGNAL and SLOTS,remove eventFilters then hide the widgets
        
    #creates directory to store the custom cursor icons
    #arg
    #returns with a)error message because couldn't create folder b)a new directory c)nothing because the directory already exists
    def create_directory(self):
         dir = QDir(self.directory_plugin)    #create a QDir object with the plugin's current path string 
            
         if ( dir.mkdir("customCursorImage") ):    #attempt to create directory
             self.directory_customCursorImage = os.path.join(self.directory_plugin , "customCursorImage" ) #create a string for the created directory to display it for the user
             msgBox = QMessageBox()
             msgBox.setText( "Folder has been successfully created\n" + (self.directory_customCursorImage) )
             msgBox.exec()  
         else:
             if(dir.exists("customCursorImage")):    #check if directory exists
                self.directory_customCursorImage = os.path.join(self.directory_plugin , "customCursorImage" ) #set the variable to the destination folder
                pass    #the folder already exists -> do nothing
             else:    #folder was not created -> raise error
                msgBox = QMessageBox()
                msgBox.setText("There was an error creating a folder")
                msgBox.exec() 
            
    #update cursor opacity
    #arg opacitySlider value
    #creates an updated customCursor with new opacity 
    def update_cursorOpacity(self, value):
        # Update the label with the current opacity
        self.labelforOpacity.setText(f"Opacity: {value}%")

        # Convert value (0-100) to opacity (0.0-1.0)
        opacity = value / 100.0
        
        if not (self.customCursor.pixmap().isNull() or self.staticCustomCursor.pixmap().isNull()):    #check if the cursors exists
            self.customCursor = self.createCustomCursor(self.staticCustomCursor.pixmap(),self.sliderforScale.value(),opacity,self.sliderforRotation.value(),self.centeredIcon.isChecked(),self.linuxArtistModeFixCheckbox.isChecked())    #create new cursor with changed opacity based on static cusror
        else:
            pass
            
    #update cursor size
    #arg cursorScale value
    #creates an updated customCursor with new scale
    def update_cursorScale(self,value):
        # Update the label with the current scale
        self.labelforScale.setText(f"Scale: {value}")
        
        # Convert value (0-100) to opacity (0.0-1.0)
        opacity = self.sliderforOpacity.value() / 100.0

        if not (self.customCursor.pixmap().isNull() or self.staticCustomCursor.pixmap().isNull()):    #check if the cursor exists
            self.customCursor = self.createCustomCursor(self.staticCustomCursor.pixmap(),value,opacity,self.sliderforRotation.value(),self.centeredIcon.isChecked(),self.linuxArtistModeFixCheckbox.isChecked())    #create new cursor with the changed scale based on static cursor

            self.labelforWidth.setText(f"Width: {self.customCursor.pixmap().size().width() }")    #update the text of labels
            self.labelforHeight.setText(f"Height: {self.customCursor.pixmap().size().height() }")
        else:
            pass

    #changes the offset of the cursor icon if it has centered orientation
    #arg
    #creates an updated customCursor with a changed offset
    def centerHotspot(self):
        #if checkbox is checked->change the cursor icon offset
        #pass True as arg for constructor
        if  self.centeredIcon.isChecked():
            if not (self.customCursor.pixmap().isNull() or self.staticCustomCursor.pixmap().isNull()):    #check if the cursor exists
                opacity = self.sliderforOpacity.value() / 100.0
                self.customCursor = self.createCustomCursor(self.staticCustomCursor.pixmap(),self.sliderforScale.value(),opacity,self.sliderforRotation.value(),True,self.linuxArtistModeFixCheckbox.isChecked())   
            else:
                pass
        #otherwise if the pixmap is not null  and the checkbox is NOT checked -> change offset back
        else:
            if not (self.customCursor.pixmap().isNull() or self.staticCustomCursor.pixmap().isNull()):    #check if the cursor exists
                opacity = self.sliderforOpacity.value() / 100.0
                self.customCursor = self.createCustomCursor(self.staticCustomCursor.pixmap(),self.sliderforScale.value(),opacity,self.sliderforRotation.value(),False,self.linuxArtistModeFixCheckbox.isChecked())   
            else:
                pass
            
    def linuxArtistModeFix(self):
        #if checkbox is checked->change the cursor icon vertical offset
        #pass True as arg for constructor
        if  self.linuxArtistModeFixCheckbox.isChecked():
            if not (self.customCursor.pixmap().isNull() or self.staticCustomCursor.pixmap().isNull()):    #check if the cursor exists
                opacity = self.sliderforOpacity.value() / 100.0
                self.customCursor = self.createCustomCursor(self.staticCustomCursor.pixmap(),self.sliderforScale.value(),opacity,self.sliderforRotation.value(),self.centeredIcon.isChecked(),True)   
            else:
                pass
        #otherwise if the pixmap is not null  and the checkbox is NOT checked -> change offset back
        else:
            if not (self.customCursor.pixmap().isNull() or self.staticCustomCursor.pixmap().isNull()):    #check if the cursor exists
                opacity = self.sliderforOpacity.value() / 100.0
                self.customCursor = self.createCustomCursor(self.staticCustomCursor.pixmap(),self.sliderforScale.value(),opacity,self.sliderforRotation.value(),self.centeredIcon.isChecked(),False)   
            else:
                pass

           
    def update_cursorRotation(self,value):
        # Update the label with the current scale
        self.labelforRotation.setText(f"Rotation(in degrees): {value}")
        
        # Convert value (0-100) to opacity (0.0-1.0)
        opacity = self.sliderforOpacity.value() / 100.0

        if not (self.customCursor.pixmap().isNull() or self.staticCustomCursor.pixmap().isNull()):    #check if the cursor exists
            self.customCursor = self.createCustomCursor(self.staticCustomCursor.pixmap(),self.sliderforScale.value(),opacity,value,self.centeredIcon.isChecked(),self.linuxArtistModeFixCheckbox.isChecked())    #create new cursor with the changed scale based on static cursor
        else:
            pass
   #after creating the directory for the cursor images make it writeable for current USER
   #arg directory
   #tries to make the directory writeable for file copy operation
    def make_directory_writable(self,directory):
        #Change the directory permissions to make it writable.
        try:
            os.chmod(directory, stat.S_IWUSR | stat.S_IRUSR) # Change the permission to allow write access for the owner
        except Exception as e:   
            msgBoxw = QMessageBox()
            msgBoxw.setText(f"Failed to change permissions for the destination directory in the plugin's folder: {e}")
            msgBoxw.exec()

    #open a file dialog window to open a suitable image file as a cursor image
    #arg 
    #returns with a) nothing because the "Cancel" button was clicked or b)set cursors and a new label added to gridLayout
    def open_file_dialog(self):
        options = QFileDialog.Options()
        source_file = QFileDialog.getOpenFileName(self, "Open Image File", "", "Images (*.png *.bmp *.svg *.gif *.webp);;All Files (*)", options=options)
        
        if source_file: #if the file exists and we could open it successfully
            file_name = os.path.basename(source_file[0])    #the name of the file without any "./" or "/"
            self.dbgWindow.append_to_end("Open Image file -> file_name = \n")
            try:
                destination = os.path.join(self.directory_customCursorImage + QDir.separator() + file_name) #create the destination absolute path 
                self.make_directory_writable(self.directory_customCursorImage) #make directory writable if it's not 
                
                shutil.copy(source_file[0],destination)    #copy file from source path to destination path,both absolute paths
                msgBox = QMessageBox()
                msgBox.setText(f"File has been successfully copied to plugin's folder ")
                msgBox.exec() 
                                
                #create a pixmap from the copied image so we can create the cursors
                opacity = self.sliderforOpacity.value() / 100.0
                self.sliderforScale.setValue(0) #reset the scale slider back to 0 to avoid opening a big image which size would get increased by scale value
                self.sliderforRotation.setValue(0) #reset rotation to 0
                pixmapFromImage = QPixmap(destination)
              
                if  not (pixmapFromImage.isNull()):
                    fileList = os.listdir(self.directory_customCursorImage)
                    fileList.sort()
                   #clear the model 
                   #then repopulate the model so the new item -> icon will be displayed at the correct index corresponding to the picture's order in the directory along other files
                    self.iconView.model().clear()
                    model = QStandardItemModel()
                    for filename in fileList:                   
                       if filename.lower().endswith(('.png', '.bmp', '.svg' , '.gif' , '.webp' )):
                            filePath = os.path.join(self.directory_customCursorImage + QDir.separator() + filename)	#create absolute path for image file 
                            pixmap = QPixmap(filePath)
                            if not pixmap.isNull():
                                icon = QIcon(pixmap)
                                item = QStandardItem(icon, "")
                                item.setData(filePath, self.filePathRole)  # Store file path
                                item.setData(filename,self.fileNameRole)    # Store filename
                                model.appendRow(item)
                    self.iconView.setModel(model)
                    self.iconView.viewport().update()
                    
                    #search for the new item based on the newly opened image file's name
                    # so we use the file_name var and search for the item in the model with a for-loop
                    # when found -> get its index then use that index to automatically select the icon in the viewport
                    for row in range(self.iconView.model().rowCount()):
                        item = self.iconView.model().item(row)
                        if item.data(self.fileNameRole) == file_name:
                            index = self.iconView.model().indexFromItem(item)
                            self.iconView.setCurrentIndex(index)
                            self.iconView.selectionModel().select(index, QItemSelectionModel.ClearAndSelect)
                            self.iconView.scrollTo(index)
                            break
                    
                    #when the set up is complete create the cursors
                    self.staticCustomCursor = self.createCustomCursor(pixmapFromImage,0,1.0,0,False,self.linuxArtistModeFixCheckbox.isChecked()) #an original version of the cursor which will be used to create a changing version so it's created with default values: "0" for scale and "1" for full opacity
                    self.customCursor = self.createCustomCursor(self.staticCustomCursor.pixmap(),0,opacity,0,self.centeredIcon.isChecked(),self.linuxArtistModeFixCheckbox.isChecked())  #create the changing cursor  from the static cursor
                    self.labelforWidth.setText(f"Width: {self.customCursor.pixmap().size().width() }")    #set the size labels with the size values
                    self.labelforHeight.setText(f"Height: {self.customCursor.pixmap().size().height() }")
                else:
                    msgBox = QMessageBox()
                    msgBox.setText(f"Pixmap is NULL after opening file")
                    msgBox.exec()
                
                
            except Exception as e:
                msgBox2 = QMessageBox()
                msgBox2.setText(f" Exception occured: {e} ")
                msgBox2.exec() 
                if not (os.access(destination,os.W_OK)):
                     msgBox = QMessageBox()
                     msgBox.setText(f" No WRITE access to the folder ")
                     msgBox.exec() 
                else:
                     msgBox = QMessageBox()
                     msgBox.setText(f" ERROR copying file: {destination} ")
                     msgBox.exec() 
        else:
            msgBox = QMessageBox()
            msgBox.setText(f" ERROR while opening file!")
            msgBox.exec() 

    #initialize the iconView model with the items created based on pictures 
    #arg 
    #return with a) nothing or b) filled model with items
    def initIconView_list(self):
        if ( os.path.isdir(self.directory_customCursorImage) ): #if the directory for customCursorImage exists
            fileList = os.listdir(self.directory_customCursorImage)	#save the number of items that are in the directory
            if not fileList :    #if filelist is empty -> no file can be found in the directory -> do nothing
                self.staticCustomCursor = QCursor()    #reset the cursors from previous state as the file has been deleted
                self.customCursor = QCursor()
                pass
            else:    #if there is a file 
                fileList.sort() #sort the entries                
                #create a model --> create the items with the small icons --> add the items into the model and set this model for iconView to display
                model = QStandardItemModel()
                for filename in fileList:                   
                    if filename.lower().endswith(('.png', '.bmp', '.svg' , '.gif' , '.webp' )):
                        filePath = os.path.join(self.directory_customCursorImage + QDir.separator() + filename)	#create absolute path for image file 
                        pixmap = QPixmap(filePath)
                        if not pixmap.isNull():
                            icon = QIcon(pixmap)
                            item = QStandardItem(icon, "")
                            item.setData(filePath, self.filePathRole)  # Store file path
                            item.setData(filename,self.fileNameRole)    # Store file name which can be considered a uniqe ID
                            model.appendRow(item)
                self.iconView.setModel(model)
                self.iconView.viewport().update()
                         
    def createCustomCursorFromModel_Item(self):
         #get Item based on the loaded settings:
         # if it's NOT -1 then get the corresponding item from the model and use it to create the cursor
        model = self.iconView.model()
        if  self.loadedSetting_selectedIndex != -1:
            getItem = model.item(self.loadedSetting_selectedIndex, 0)  # Row = value , column =  0
            if getItem:
                filePath = getItem.data(self.filePathRole)  # Get file path
                pixmapFromItem = QPixmap(filePath)    #create the pixmap via this absolute path then create the cursors
                self.staticCustomCursor = self.createCustomCursor(pixmapFromItem,0,1,0,False,False) 	#create a static version of the cursor with pixmap, scale:0 , opacity:1 , centered:false , rotation:0
                self.customCursor = self.createCustomCursor(self.staticCustomCursor.pixmap(), self.sliderforScale.value(), (self.sliderforOpacity.value() / 100),self.sliderforRotation.value(),self.centeredIcon.isChecked(),self.linuxArtistModeFixCheckbox.isChecked())    #create a changing version of the cursor with pixmap from the static version, scale:0 , opacity: from the slider , centered:value from checkbox , rotation:0
                    
                self.labelforWidth.setText(f"Width: {self.customCursor.pixmap().size().width() }")    #update the text of labels
                self.labelforHeight.setText(f"Height: {self.customCursor.pixmap().size().height() }")
            else:
                self.staticCustomCursor = QCursor()    #reset the cursors 
                self.customCursor = QCursor()
        else:    # if it's -1 then default back to the fist item in the model and create the cursor with it
             getItem = model.item(0, 0)  # Row = 0, column = 0
             if getItem:
                 filePath = getItem.data(self.filePathRole)  # Get file path
                 pixmapFromItem = QPixmap(filePath)    #create the pixmap via this absolute path then create the cursors
                 self.staticCustomCursor = self.createCustomCursor(pixmapFromItem,0,1,0,False,False) 	#create a static version of the cursor with pixmap, scale:0 , opacity:1 , centered:false , rotation:0
                 self.customCursor = self.createCustomCursor(self.staticCustomCursor.pixmap(),self.sliderforScale.value(), (self.sliderforOpacity.value() / 100),self.sliderforRotation.value(),self.centeredIcon.isChecked(),self.linuxArtistModeFixCheckbox.isChecked())    #create a changing version of the cursor with pixmap from the static version, scale:0 , opacity: from the slider , centered:value from checkbox , rotation:0
                    
                 self.labelforWidth.setText(f"Width: {self.customCursor.pixmap().size().width() }")    #update the text of labels
                 self.labelforHeight.setText(f"Height: {self.customCursor.pixmap().size().height() }")
             else:
                self.staticCustomCursor = QCursor()    #reset the cursors
                self.customCursor = QCursor()
                     
     #when one of the cursor icon is clicked set that one as the main cursor image           
     #arg index of clicked icon
     #return  with cursors
    def on_icon_clicked(self,index):
       #get the absolute path from the selected item
        filePath = index.data(self.filePathRole)
        if os.path.exists(filePath): #if the file exists on the given absolute path
            pixmapFromImage = QPixmap(filePath)    #create the pixmap from file
            opacity = self.sliderforOpacity.value() / 100.0    #get opacity value from slider
            scale = self.sliderforScale.value()
            rotation = self.sliderforRotation.value()

            self.staticCustomCursor = self.createCustomCursor(pixmapFromImage,0,1,0,False,self.linuxArtistModeFixCheckbox.isChecked()) 
            self.customCursor = self.createCustomCursor(self.staticCustomCursor.pixmap(),scale,opacity,rotation,self.centeredIcon.isChecked(),self.linuxArtistModeFixCheckbox.isChecked())
            
            self.labelforWidth.setText(f"Width: {self.customCursor.pixmap().size().width() }")    #update the text of labels
            self.labelforHeight.setText(f"Height: {self.customCursor.pixmap().size().height() }")
            
            #set highlight for the clicked icon
            self.iconView.setCurrentIndex(index)
        else: #delete the item from the layout and rearrange the remaining ones
            model = self.iconView.model()
            if model:
                model.removeRow(index.row())
            QMessageBox.warning(self, "File Missing", f"The file {filePath} was not found and has been removed.")
            self.iconView.clearSelection()
            self.staticCustomCursor = QCursor()    #reset the cursors
            self.customCursor = QCursor()  
    
    #function to check if a brush tool was turned on or off then send a custom EVENT based on the bool value
    def checkBrushTool(self,checked):    
        if (checked):    #one of the buttons EMITTED a toggled SIGNAL and it was true so one of them was turned ON
            brushEvent = BrushToggledONEvent()
            QMdiArea = findQMdiArea()   
            QCoreApplication.postEvent(QMdiArea, brushEvent)
        elif not (checked):    #one of the buttons EMITTED a toggled SIGNAL and it was false so one of them was turned OFF
            brushEvent = BrushToggledOFFEvent()
            QMdiArea = findQMdiArea()   
            QCoreApplication.postEvent(QMdiArea, brushEvent)

                        
    #event filter that handles logic when to show the cursor 		
    def eventFilter(self, obj, event):
        q_app = QCoreApplication.instance()
        if (event.type() == QEvent.Enter):    #if mouse pointer enters the QMdiArea area
            if ( not obj == self.iconView.viewport() ):  
                q_win = Krita.instance().activeWindow().qwindow()
                KritaShape_KisToolBrush = q_win.findChild(QToolButton,"KritaShape/KisToolBrush")
                KritaShape_KisToolMultiBrush = q_win.findChild(QToolButton,"KritaShape/KisToolMultiBrush")
                KritaShape_KisToolLazyBrush = q_win.findChild(QToolButton,"KritaShape/KisToolLazyBrush")
                KritaShape_KisToolDynamicBrush = q_win.findChild(QToolButton,"KritaShape/KisToolDyna")
                if (KritaShape_KisToolBrush.isChecked() or  KritaShape_KisToolMultiBrush.isChecked() or KritaShape_KisToolLazyBrush.isChecked() or KritaShape_KisToolDynamicBrush.isChecked() ):    #check if a brush tool is currently selected and the cursor is not set up yet
                    if (self.isCustomCursorApplied == False):    #brush tool button is selected but custom cursor is not applied yet
                        q_app.setOverrideCursor(self.customCursor)
                        self.isCustomCursorApplied = True    ##set the cursor status tracking var to True
                    if (self.isCustomCursorApplied == True):    #brush tool button is selected but custom cursor is already applied
                        pass
                else:    #brush tool button was NOT selected
                    #q_app.restoreOverrideCursor()
                    while q_app.overrideCursor():
                        q_app.restoreOverrideCursor()
                    self.isCustomCursorApplied = False
            else:    #if  qwindow or qmdiarea is a nullptr do nothing
                pass
        elif (event.type() == QEvent.Leave):    #if mouse pointer leaves the QMdia area
            if (not obj == self.iconView.viewport() ):
                q_win = Krita.instance().activeWindow().qwindow()  
                KritaShape_KisToolBrush = q_win.findChild(QToolButton,"KritaShape/KisToolBrush")
                KritaShape_KisToolMultiBrush = q_win.findChild(QToolButton,"KritaShape/KisToolMultiBrush")
                KritaShape_KisToolLazyBrush = q_win.findChild(QToolButton,"KritaShape/KisToolLazyBrush")
                KritaShape_KisToolDynamicBrush = q_win.findChild(QToolButton,"KritaShape/KisToolDyna")
                if (KritaShape_KisToolBrush.isChecked() or  KritaShape_KisToolMultiBrush.isChecked() or KritaShape_KisToolLazyBrush.isChecked() or KritaShape_KisToolDynamicBrush.isChecked() ):    #check if a brush tool is currently selected
                    #q_app.restoreOverrideCursor()
                    while q_app.overrideCursor():
                        q_app.restoreOverrideCursor()
                    self.isCustomCursorApplied = False #set the cursor status tracking var to False
                else:    #no brush tool is selected in the time of leave event, unset Cursor on OpenGLWidget
                    #q_app.restoreOverrideCursor()
                    while q_app.overrideCursor():
                        q_app.restoreOverrideCursor()
                    self.isCustomCursorApplied = False
        
        #toggled ON event handling
        elif (event.type() == BrushToggledONEvent.EventType):    #if a brush tool was toggled -> check where the mouse cursor is -> then turn on/off the custom cursor 
            cursor_pos = QCursor.pos()
            local_pos = obj.mapFromGlobal(cursor_pos)
            if obj.rect().contains(local_pos):    #if the cursor is in the MdiArea check if any of the tools are checked
                q_win = Krita.instance().activeWindow().qwindow()
                KritaShape_KisToolBrush = q_win.findChild(QToolButton,"KritaShape/KisToolBrush")
                KritaShape_KisToolMultiBrush = q_win.findChild(QToolButton,"KritaShape/KisToolMultiBrush")
                KritaShape_KisToolLazyBrush = q_win.findChild(QToolButton,"KritaShape/KisToolLazyBrush")
                KritaShape_KisToolDynamicBrush = q_win.findChild(QToolButton,"KritaShape/KisToolDyna")
                if (KritaShape_KisToolBrush.isChecked() or  KritaShape_KisToolMultiBrush.isChecked() or KritaShape_KisToolLazyBrush.isChecked() or KritaShape_KisToolDynamicBrush.isChecked() and self.isCustomCursorApplied == False ):    #if a BRUSH tool was toggled ON from a NON-brush tool
                    q_app.setOverrideCursor(self.customCursor)
                    self.isCustomCursorApplied = True    ##set the cursor status tracking var to True
                elif (KritaShape_KisToolBrush.isChecked() or  KritaShape_KisToolMultiBrush.isChecked() or KritaShape_KisToolLazyBrush.isChecked() or KritaShape_KisToolDynamicBrush.isChecked() and self.isCustomCursorApplied == True):    #if brush tool is selected but custom cursor is already set -> do nothing
                    pass
            else:    #if event happened outside of the area do nothing
                pass
                
            return True    #we signal that the event was handled and doesn't need to be further propagated
            
        #toggled OFF event handling
        elif (event.type() == BrushToggledOFFEvent.EventType):
            cursor_pos = QCursor.pos()
            local_pos = obj.mapFromGlobal(cursor_pos)
            if obj.rect().contains(local_pos):    #if the cursor is in the MdiArea check what tool is selected 
                q_win = Krita.instance().activeWindow().qwindow()
                KritaShape_KisToolBrush = q_win.findChild(QToolButton,"KritaShape/KisToolBrush")
                KritaShape_KisToolMultiBrush = q_win.findChild(QToolButton,"KritaShape/KisToolMultiBrush")
                KritaShape_KisToolLazyBrush = q_win.findChild(QToolButton,"KritaShape/KisToolLazyBrush")
                KritaShape_KisToolDynamicBrush = q_win.findChild(QToolButton,"KritaShape/KisToolDyna")
                if (not KritaShape_KisToolBrush.isChecked() or  not KritaShape_KisToolMultiBrush.isChecked() or not KritaShape_KisToolLazyBrush.isChecked() or not KritaShape_KisToolDynamicBrush.isChecked() ):    #check if a brush tool is currently selected or not
                    #q_app.restoreOverrideCursor()    #restore default cursor if a non-brush tool is selected 
                    while q_app.overrideCursor():
                        q_app.restoreOverrideCursor()
                    self.isCustomCursorApplied = False #set the cursor status tracking var to false
                else:
                    pass    #if we switched from one brush tool to another do nothing
            else:    #if event happened outside of the area restore cursor just in case
                #q_app.restoreOverrideCursor()    #restore default cursor if a non-brush tool is selected
                while q_app.overrideCursor():
                    q_app.restoreOverrideCursor()
                self.isCustomCursorApplied = False #set the cursor tracking var to false
                 
            return True    #we signal that the event was handled and doesn't need to be further propagated
            
        # Handle iconView viewport mouseevent to prevent item deselection
        elif obj == self.iconView.viewport() and event.type() in (
            QEvent.MouseButtonPress,
            QEvent.MouseMove,
            QEvent.MouseButtonRelease
        ):
            index = self.iconView.indexAt(event.pos())
            if not index.isValid():
                # Click on empty space, do nothing to keep selection
                return True
        else:    #if somehow qwindow or qmdiarea is a nullptr do nothing
            pass       
     
        return super().eventFilter(obj, event)
		
		
    def canvasChanged(self, canvas):
        pass
        
#add the dock widget to krita instance
Krita.instance().addExtension(DockerUISettingsManager(Krita.instance()))
Krita.instance().addDockWidgetFactory(DockWidgetFactory("customBrushCursorDocker", DockWidgetFactoryBase.DockRight, customBrushCursorDocker))


