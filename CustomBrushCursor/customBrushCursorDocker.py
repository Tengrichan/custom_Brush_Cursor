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
        QGridLayout,
        QSlider,
        QFileDialog,
        QLayoutItem)
        
from krita import (
        DockWidget,
        DockWidgetFactory,
        DockWidgetFactoryBase)

from PyQt5.QtCore import (
        Qt,
        QDir,
        QEvent,
        QCoreApplication)

from PyQt5.QtGui import (
        QColor,
        QPainter,
        QPixmap,
        QPalette,
        QCursor,
        QTransform,
        QMouseEvent,
        QTabletEvent)
  

import os
import shutil
import stat

from pathlib import Path #module to handle paths

def find_current_canvas():
    q_window = Krita.instance().activeWindow().qwindow() #Return a handle to the QMainWindow widget. This is useful to e.g. parent dialog boxes and message box
    #q_stacked_widget = q_window.centralWidget()
    #canvas = q_stacked_widget.findChild(QOpenGLWidget) 
    canvas = q_window.findChild(QMdiArea)
    return canvas    #return with an object


def isDocumentOpen():
    app = Krita.instance() # get the application
    documentsOpen = app.documents() # get the open documents
    documentCount = len(documentsOpen) # get how many documents are opened
    return documentCount #return with the length of documentCount list
    
class extendedLabel(QLabel):
    
    def __init__(self,**kwargs):
        super().__init__(**kwargs)
        self.info = ""
        
    def setInfo(self,argInfo):
        self.info = argInfo
    
    def getInfo(self):
        return self.info
        
    
class customBrushCursorDocker(DockWidget):

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Custom Brush Cursor")
        #directory stuff
        self.directory_plugin = str( os.path.dirname( os.path.realpath( __file__ ) ) )
        self.directory_customCursorImage = str("")
        #cursor related stuff
        self.selected_label = None
        self.pixmap = QPixmap()    #cursor pixmap
        self.flip = False    #variable to keep track whether to flip or not 
        self.opacity = 0    #variable to keep track of opacity
        self.customCursor = QCursor()        #the changing version of cursor
        self.staticCustomCursor = QCursor() #an original version of custom cursor which will be used for opacity and scale as a basis
               
        #GUI init
        self.initGUI()
    

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
        painter.drawPixmap(0, 0, pixmap) #draws a pixmap at (x,y) ; (x,y) specifies top-left origin ; default is (0,0)
        painter.end()
        return new_pixmap

    #creates the custom cursor
    #arg pixmap,scale,opacity
    #return QCursor
    def createCustomCursor(self,pixmap,scaleValue,opacity,crosshair):
        scaled_pixmap = self.pixmapScale(pixmap,scaleValue)      #scale the pixmap with input scale value 
        #scaled_pixmap = QPixmap(pixmap).scaled(256, 256, Qt.IgnoreAspectRatio)    #create a scaled pixmap that will be shown
        scaled_pixmap = self.changeOpacity(scaled_pixmap,opacity)       #change the opacity of the already scaled pixmap with opacity
        #check whether the orientation of the cursor icon is centered like a crosshair or not
        #if it's centered then use a different offset
        if crosshair == True:
            qCursor = QCursor(scaled_pixmap,int(scaled_pixmap.width()/2),int(scaled_pixmap.height()/2) + 1 )
        else:
            qCursor = QCursor(scaled_pixmap,0,scaled_pixmap.height() + 1)     #create a cursor object from scaledImage and set its coordinates X=0 and Y=move the image up by its height because its orientation
       #qCursor = QCursor(scaled_pixmap,0,0 )     #create a cursor object from scaledImage and set its coordinates X=0 and Y=0
        return  qCursor	
    
    def initGUI(self):
        self.mainWidget = QWidget(self)
        self.setWidget(self.mainWidget)
        
        #create three widgets specifically to separate the button from the options
        self.buttonWidget = QWidget(self.mainWidget)
        self.optionsWidget = QWidget(self.mainWidget)
        self.listImagesWidget = QListWidget(self.mainWidget)
        
        #Create a turn on/off button; its parent is the dockwidget itself
        self.buttonStatus = QPushButton("Activate", self)
        self.buttonStatus.setCheckable(True)
        self.buttonStatus.toggled.connect(self.toggleState)
        
        buttonlayout = QVBoxLayout()
        buttonlayout.addWidget(self.buttonStatus, alignment=Qt.AlignTop | Qt.AlignHCenter)
        self.buttonWidget.setLayout(buttonlayout)
        
        #set gridlayout for listImageswidget
        self.gridLayout = QGridLayout()
        #self.gridLayout.setVerticalSpacing(3)    #set spacing between rows
        self.listImagesWidget.setLayout(self.gridLayout)

        
        #Open file button to browse for custom image to be used as a custom cursor,on click calls "open_file_dialog'" function
        self.open_button = QPushButton("Open image file...")
        self.open_button.clicked.connect(self.open_file_dialog)
        
        # Create a label to show the current opacity value
        self.labelforOpacity = QLabel("Opacity: 50%", self.optionsWidget)
        
        # Create a slider for opacity
        self.sliderforOpacity = QSlider(Qt.Horizontal, self.optionsWidget)
        self.sliderforOpacity.setRange(0, 100)  # Range from 0 to 100
        self.sliderforOpacity.setValue(50)  # Default value (100% opacity)
        self.sliderforOpacity.valueChanged.connect(self.update_cursorOpacity)     
        
        
        # Create a label to show scaling
        self.labelforScale = QLabel("Scale: 0", self.optionsWidget)
        
        # Create a slider for scaling
        self.sliderforScale = QSlider(Qt.Horizontal, self.optionsWidget)
        self.sliderforScale.setRange(-10, 10)  # Range from -10 to 10
        self.sliderforScale.setSingleStep(1)
        self.sliderforScale.setPageStep(1)
        self.sliderforScale.setValue(0)  # Default value (-1 or 0 or 1 for original scale)
        self.sliderforScale.valueChanged.connect(self.update_cursorScale)     
        
        #create labels for cursor size
        self.labelforWidth = QLabel("Width: -", self.optionsWidget)
        self.labelforHeight = QLabel("Height: -", self.optionsWidget)
        
        #create a checkbox to switch between two different offsets 
        self.centeredIcon = QCheckBox("Centered cursor icon",self)
        self.centeredIcon.stateChanged.connect(self.centerHotspot)
		
        optionslayout = QVBoxLayout()
        optionslayout.addWidget(self.open_button)
      
        optionslayout.addWidget(self.labelforOpacity)
        optionslayout.addWidget(self.sliderforOpacity)
        
        optionslayout.addWidget(self.labelforScale)
        optionslayout.addWidget(self.sliderforScale)
        
        optionslayout.addWidget(self.labelforWidth)
        optionslayout.addWidget(self.labelforHeight)
      
        #optionslayout.addWidget(self.flipButton, alignment=Qt.AlignTop | Qt.AlignHCenter )
        optionslayout.addWidget(self.centeredIcon, alignment=Qt.AlignTop | Qt.AlignHCenter )
        
        self.optionsWidget.setLayout(optionslayout)
        
        #widget layout
        layout = QVBoxLayout()
        layout.addWidget(self.buttonWidget, alignment=Qt.AlignTop | Qt.AlignHCenter)
        layout.addWidget(self.optionsWidget, alignment=Qt.AlignTop)
        layout.addWidget(self.listImagesWidget,alignment = Qt.AlignTop)
        self.mainWidget.setLayout(layout)
        
        #don't show the options by default until the button is clicked 
        self.optionsWidget.hide()
        self.listImagesWidget.hide()
	
 	
    def closeEvent(self, event):
        self.release_core_app()
        return super().closeEvent(event)


    def hook_core_app(self):
        """ add hook to core application. """
        if (isDocumentOpen() >=1):
            canvas = find_current_canvas()
            canvas.installEventFilter(self)
            self.optionsWidget.show()
            self.listImagesWidget.show()

    def release_core_app(self):
        """ remove hook from core application. """
        canvas = find_current_canvas()
        canvas.removeEventFilter(self)
        self.optionsWidget.hide()
        self.listImagesWidget.hide()
      
    #main plugin ON/OFF button
    #arg button's toggled value
    #calls a group of functions to run based on the value
    def toggleState(self, checked):
        #If we activated the button/plugin
        if checked:
            self.buttonStatus.setText('Deactivate')    #set the text on the button to "Deactivate"
            self.create_directory()    #create directory for the images if it doesn't exist already
            self.checkforExistingFile()    #check for existing files to apply one by default
            self.hook_core_app()    
        else:
            self.buttonStatus.setText('Activate')    #set the text on the button to "Activate"
            self.clean_listImagesWidget()
            self.release_core_app() 
        
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
            self.customCursor = self.createCustomCursor(self.staticCustomCursor.pixmap(),self.sliderforScale.value(),opacity,self.centeredIcon.isChecked())    #create new cursor with changed opacity based on static cusror
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
            self.customCursor = self.createCustomCursor(self.staticCustomCursor.pixmap(),value,opacity,self.centeredIcon.isChecked())    #create new cursor with the changed scale based on static cursor

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
                self.customCursor = self.createCustomCursor(self.staticCustomCursor.pixmap(),self.sliderforScale.value(),opacity,True)   
            else:
                pass
        #otherwise if the pixmap is not null  and the checkbox is NOT checked -> change offset back
        else:
            if not (self.customCursor.pixmap().isNull() or self.staticCustomCursor.pixmap().isNull()):    #check if the cursor exists
                opacity = self.sliderforOpacity.value() / 100.0
                self.customCursor = self.createCustomCursor(self.staticCustomCursor.pixmap(),self.sliderforScale.value(),opacity,False)   
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
        source_file = QFileDialog.getOpenFileName(self, "Open Image File", "", "Images (*.png *.jpg *.jpeg *.bmp *.svg );;All Files (*)", options=options)
        
        if source_file: #if the file exists and we could open it successfully
            file_name = os.path.basename(source_file[0])    #the name of the file without any "./" or "/"
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
                pixmapFromImage = QPixmap(destination)
              
                if  not (pixmapFromImage.isNull()):
                    self.staticCustomCursor = self.createCustomCursor(pixmapFromImage,0,1.0,False) #an original version of the cursor which will be used to create a changing version so it's created with default values: "0" for scale and "1" for full opacity
                    self.customCursor = self.createCustomCursor(self.staticCustomCursor.pixmap(),0,opacity,self.centeredIcon.isChecked())  #create the changing cursor  from the static cursor
                    self.labelforWidth.setText(f"Width: {self.customCursor.pixmap().size().width() }")    #set the size labels with the size values
                    self.labelforHeight.setText(f"Height: {self.customCursor.pixmap().size().height() }")
                    
                    #when a new image is opened,create a new icon of it and add it to listitemwidget's layout
                    label = extendedLabel()    #create an instance of label from extendedLabel()
                    label.setInfo(destination)    #save the absolute path via setInfo method
                    pixmap = QPixmap(destination).scaled(32, 32, Qt.KeepAspectRatio)    #create a scaled pixmap that will be shown
                    label.setPixmap(pixmap)    #set pixmap for label
                    label.mousePressEvent = lambda event, label=label: self.image_clicked(label)    #create a mouse event for when label is clicked/selected
                    index = self.gridLayout.count()
                    label.setFixedHeight(32)    #set label's height to a fixed 32pixel
                    self.gridLayout.addWidget(label,index // 4 , index % 4)  # 4 images per row    #add the label to the parent widget with gridlayout    
                    
                    rows = self.gridLayout.rowCount()      #get the number of rows
                    self.listImagesWidget.setMinimumHeight(rows * 40)    #set minimum height of the images widget according to the number of rows                
                    # Clear selection
                    if self.selected_label:
                        self.selected_label.setStyleSheet("border: none;")
     
                    # Set new selection
                    self.selected_label = label
                    self.selected_label.setStyleSheet("border: 1px solid blue;") 
                else:
                    msgBox = QMessageBox()
                    msgBox.setText(f"Pixmap is NULL after opening file")
                    msgBox.exec()
                
                
            except Exception as e:
                msgBox2 = QMessageBox()
                msgBox2.setText(f" Exception occured: {e} ")
                msgBox2.exec() 
                if not (os.access(destination,os.W_OK)):
                     #self.make_directory_writable(self.directory_customCursorImage)
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

    #function to load in an already existing cursor image that's in the folder already when the plugin is activated
    #arg 
    #return with a) nothing or b) filled gridLayout with labels; set cursors
    def checkforExistingFile(self):
        if ( os.path.isdir(self.directory_customCursorImage) ): #if the directory for customCursorImage exists
            fileList = os.listdir(self.directory_customCursorImage)	#save the number of items that are in the directory
            if not fileList :    #if filelist is empty -> no file can be found in the directory -> do nothing
                self.staticCustomCursor = QCursor()    #reset the cursors from previous state as the file has been deleted
                self.customCursor = QCursor()
                pass
            else:    #if there is a file 
                fileList.sort() #sort the entries 
                opacity = self.sliderforOpacity.value() / 100.0
                self.sliderforScale.setValue(0) 
                
                #create the labels with the small icons 
                index = 0
                for filename in fileList:                   
                    if filename.endswith(('.png', '.jpg', '.jpeg', '.bmp', '.svg' )):
                        filePath = os.path.join(self.directory_customCursorImage + QDir.separator() + filename)	#create absolute path for image file 
                        label = extendedLabel()    #create an instance of label from extendedLabel()
                        label.setInfo(filePath)    #save the absolute path via setInfo method
                        pixmap = QPixmap(filePath).scaled(32, 32, Qt.KeepAspectRatio)    #create a scaled pixmap that will be shown
                        label.setPixmap(pixmap)    #set pixmap for label
                        label.mousePressEvent = lambda event, label=label: self.image_clicked(label)    #create a mouse event for when label is clicked/selected
                        label.setFixedHeight(32)    #set label's height to a fixed 32pixel
                        self.gridLayout.addWidget(label,index // 4 , index % 4)  # 4 images per row    #add the label to the parent widget with gridlayout
                        index += 1    
                
                rows = self.gridLayout.rowCount()  
                self.listImagesWidget.setMinimumHeight(rows * 40)    #set minimum hight of the images widget
                #create the cursor for the first image
                item = self.gridLayout.itemAt(0)    #get the first QLayoutItem from the gridLayout
                labelWidget = item.widget()    #get the widget from  it
                pathFromLabel = labelWidget.getInfo()    #get the corresponding absolute path to the image from the label
                pixmapFromLabel = QPixmap(pathFromLabel)    #create the pixmap via this absolute path then create the cursors
                self.staticCustomCursor = self.createCustomCursor(pixmapFromLabel,0,1,False) 
                self.customCursor = self.createCustomCursor(self.staticCustomCursor.pixmap(),0,opacity,self.centeredIcon.isChecked())    
                    
                self.labelforWidth.setText(f"Width: {self.customCursor.pixmap().size().width() }")    #update the text of labels
                self.labelforHeight.setText(f"Height: {self.customCursor.pixmap().size().height() }")
                
                # Set the layout border on the first label 
                self.selected_label = labelWidget
                self.selected_label.setStyleSheet("border: 1px solid blue;")
                
     #when one of the cursor image is clicked set that one as the main cursor image           
     #arg label
     #return  with cursors
    def image_clicked(self,label):
       #get the absolute path from the selected label
        filePathfromImage = label.getInfo()
        if os.path.exists(filePathfromImage): #if the file exists on the given absolute path
            pixmapFromImage = QPixmap(filePathfromImage)    #create the pixmap from file
            opacity = self.sliderforOpacity.value() / 100.0    #get opacity value from slider
            self.sliderforScale.setValue(0)
            self.staticCustomCursor = self.createCustomCursor(pixmapFromImage,0,1,False) 
            self.customCursor = self.createCustomCursor(self.staticCustomCursor.pixmap(),0,opacity,self.centeredIcon.isChecked())
            
            self.labelforWidth.setText(f"Width: {self.customCursor.pixmap().size().width() }")    #update the text of labels
            self.labelforHeight.setText(f"Height: {self.customCursor.pixmap().size().height() }")
            
            # Clear selection
            if self.selected_label:
                self.selected_label.setStyleSheet("border: none;")
     
            # Set new selection
            self.selected_label = label
            self.selected_label.setStyleSheet("border: 1px solid blue;")
            
        else: #delete the label from the layout and rearrange the remaining ones
            self.gridLayout.removeWidget(label)    #first we remove it from the layout
            label.deleteLater() #schedule the label for deletion to free up resources and to avoid conflict(s)
            self.selected_label = None    #change the selected_label variable to none
            rows = self.gridLayout.rowCount()      #get the row count after the deletion of label
            self.listImagesWidget.setMinimumHeight(rows * 40)    #reset minimum hight of the images widget
     
    #remove the label widgets from listImagesWidget
    #arg 
    #return empty gridLayout
    def clean_listImagesWidget(self):     
        for i in reversed(range(self.gridLayout.count())):  # Use reversed to avoid indexing issues
            item = self.gridLayout.itemAt(i)
            widget = item.widget()
            if isinstance(widget, QLabel):
                self.gridLayout.removeWidget(widget)  # Remove the widget from the layout
                widget.deleteLater()  # Properly delete the widget   
        self.gridLayout.update()
        self.selected_label = None
        self.staticCustomCursor = QCursor()    #reset the cursors from previous state as the plugin has been turned off
        self.customCursor = QCursor()
    
    #event filter that handles logic when to show the cursor 		
    def eventFilter(self, obj, event):
        q_app = QCoreApplication.instance()
        if (event.type() == QEvent.Enter):    #if mouse pointer enters the area
            canvas = find_current_canvas()
            if not (Krita.instance().activeWindow().qwindow() == None):
                q_win = Krita.instance().activeWindow().qwindow()
                KritaShape_KisToolBrush = q_win.findChild(QToolButton,"KritaShape/KisToolBrush")
                KritaShape_KisToolMultiBrush = q_win.findChild(QToolButton,"KritaShape/KisToolMultiBrush")
                KritaShape_KisToolLazyBrush = q_win.findChild(QToolButton,"KritaShape/KisToolLazyBrush")
                if (KritaShape_KisToolBrush.isChecked() or  KritaShape_KisToolMultiBrush.isChecked() or KritaShape_KisToolLazyBrush.isChecked() ):    #check if a brush tool is currently selected
                    q_app.setOverrideCursor(self.customCursor)
                else:
                    q_app.restoreOverrideCursor()
            else:
                pass
        elif (event.type() == QEvent.Leave):
             q_app.restoreOverrideCursor()
            
        return super().eventFilter(obj, event)
		
		
    def canvasChanged(self, canvas):
        pass
        
#add the dock widget to krita instance
Krita.instance().addDockWidgetFactory(DockWidgetFactory("customBrushCursorDocker", DockWidgetFactoryBase.DockRight, customBrushCursorDocker))

