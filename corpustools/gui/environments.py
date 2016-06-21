from .imports import *
from .widgets import SegmentSelectionWidget, SegmentSelectDialog
from corpustools.corpus.classes.lexicon import EnvironmentFilter

class EnvironmentDialog(QDialog):
    rowToAdd = Signal(str)
    def __init__(self, inventory,parent=None):
        QDialog.__init__(self,parent)

        self.inventory = inventory

        layout = QVBoxLayout()

        layout.setAlignment(Qt.AlignTop | Qt.AlignLeft)

        self.lhsEnvFrame = QGroupBox('Left hand side')

        self.rhsEnvFrame = QGroupBox('Right hand side')

        lhsEnvLayout = QVBoxLayout()

        lhsEnvLayout.setAlignment(Qt.AlignTop | Qt.AlignLeft)

        rhsEnvLayout = QVBoxLayout()

        rhsEnvLayout.setAlignment(Qt.AlignTop | Qt.AlignLeft)

        self.lhs = SegmentSelectionWidget(self.inventory, exclusive = True)

        self.rhs = SegmentSelectionWidget(self.inventory, exclusive = True)

        lhsEnvLayout.addWidget(self.lhs)
        rhsEnvLayout.addWidget(self.rhs)

        self.lhsEnvFrame.setLayout(lhsEnvLayout)

        self.rhsEnvFrame.setLayout(rhsEnvLayout)
        envFrame = QFrame()

        envLayout = QHBoxLayout()

        envLayout.addWidget(self.lhsEnvFrame)
        envLayout.addWidget(self.rhsEnvFrame)

        envFrame.setLayout(envLayout)

        layout.addWidget(envFrame)

        self.oneButton = QPushButton('Add')
        self.anotherButton = QPushButton('Add and create another')
        self.cancelButton = QPushButton('Cancel')
        self.acLayout = QHBoxLayout()
        self.acLayout.addWidget(self.oneButton, alignment = Qt.AlignLeft)
        self.acLayout.addWidget(self.anotherButton, alignment = Qt.AlignLeft)
        self.acLayout.addWidget(self.cancelButton, alignment = Qt.AlignLeft)
        self.oneButton.clicked.connect(self.one)
        self.anotherButton.clicked.connect(self.another)
        self.cancelButton.clicked.connect(self.reject)

        acFrame = QFrame()
        acFrame.setLayout(self.acLayout)

        layout.addWidget(acFrame, alignment = Qt.AlignLeft)
        self.addOneMore = False
        self.setLayout(layout)
        #self.setFixedSize(self.sizeHint())
        self.setWindowTitle('Create bigram')

    def one(self):
        self.addOneMore = False
        self.accept()

    def another(self):
        self.addOneMore = True
        self.accept()

    def reset(self):
        self.lhs.clearAll()
        self.rhs.clearAll()

    def accept(self):
        lhs = self.lhs.value()
        rhs = self.rhs.value()

        if lhs == '':
            reply = QMessageBox.critical(self,
                    "Missing information", "Please specify a left hand of the bigram.")
            return
        if rhs == '':
            reply = QMessageBox.critical(self,
                    "Missing information", "Please specify a right hand of the bigram.")
            return

        env = lhs, rhs
        self.rowToAdd.emit([env])
        if not self.addOneMore:
            QDialog.accept(self)
        else:
            self.reset()

class EnvironmentSegmentWidget(QWidget):
    def __init__(self, inventory, parent = None, middle = False, enabled = True, preset_label = False, show_full_inventory=False):
        QWidget.__init__(self, parent)
        self.inventory = inventory
        self.segments = set()
        self.features = set()
        self.enabled = enabled
        self.show_full_inventory = show_full_inventory

        self.middle = middle

        layout = QVBoxLayout()
        if self.middle:
            lab = '_\n\n{}'
        else:
            lab = '{}'
        self.mainLabel = QPushButton(lab)
        self.mainLabel.setStyleSheet("padding: 4px")

        layout.addWidget(self.mainLabel)

        self.setLayout(layout)

        if self.enabled:
            self.menu = QMenu(self)
            segmentAct = QAction("Add segments", self, triggered=self.selectSegments)
            featureAct = QAction("Add features", self, triggered=self.selectFeatures)
            arbitraryAct = QAction("Match anything here", self, triggered=self.addArbitrary)
            clearAct = QAction("Clear selection", self, triggered=self.clearSelection)
            self.menu.addAction(segmentAct)
            self.menu.addAction(featureAct)
            if not self.middle:
                nonSegSelectMenu = self.menu.addMenu('Add non-segment symbol')
                for symbol in self.inventory.non_segment_symbols:
                    nonSegSelectMenu.addAction(QAction(symbol, self, triggered=self.addNonSegSymbol))
            self.menu.addAction(arbitraryAct)
            self.menu.addAction(clearAct)
            if not self.middle:
                deleteAct = QAction("Delete", self, triggered=self.deleteSelection)
                self.menu.addAction(deleteAct)
            self.mainLabel.setMenu(self.menu)
        else:
            self.mainLabel.setEnabled(False)

        if preset_label:
            self.segments = preset_label.segments
            self.features = preset_label.features
            self.updateLabel()

    def addNonSegSymbol(self):
        self.segments.add(self.sender().text())
        self.updateLabel()

    def addArbitrary(self):
        self.segments = set(self.inventory.segs)
        self.updateLabel()

    def clearSelection(self):
        self.segments = set()
        self.features = set()
        self.updateLabel()

    def deleteSelection(self):
        self.deleteLater()

    def updateLabel(self):
        labelText = self.generateDisplayText()
        if not labelText:
             labelText = '{}'
        if self.middle:
            labelText = '_\n\n{}'.format(labelText)
        self.mainLabel.setText(labelText)

    def generateDisplayText(self):

        displayList = list()
        if len(self.segments) == len(self.inventory.segs):
            if self.show_full_inventory:
                displayList = ','.join(self.segments)
            else:
                displayList = '{*}'
        else:
            displayList.extend(self.segments)
            displayList.extend(self.features)
            displayList = ','.join(displayList)
            displayList = '{{{}}}'.format(displayList)

        return displayList

    def selectSegments(self):
        dialog = SegmentSelectDialog(self.inventory, self.segments, self, start_pressed=self.segments)
        if dialog.exec_():
            self.segments = set(dialog.value())
            self.updateLabel()

    def selectFeatures(self):
        dialog = SegmentSelectDialog(self.inventory, self.segments, self, use_features=True)
        if dialog.exec_():
            self.features = set(dialog.value())
            self.updateLabel()

    def value(self):
        # if '*' in self.mainLabel.text():
        #     return ['*']

        segs = [s for s in self.segments]
        if self.features:
            more_segs = self.inventory.features_to_segments(self.features)
            segs.extend(more_segs)
            segs = list(set(segs))
        return segs

    def displayValue(self):
        return self.generateDisplayText()


class EnvironmentSelectWidget(QGroupBox):
    def __init__(self, inventory, parent = None, middle = True, show_full_inventory=False):
        QGroupBox.__init__(self,'Environments',parent)
        self.parent = parent
        self.middle = middle
        self.inventory = inventory
        self.show_full_inventory = show_full_inventory

        layout = QVBoxLayout()

        scroll = QScrollArea()
        self.environmentFrame = QWidget()
        lay = QBoxLayout(QBoxLayout.TopToBottom)
        self.addButton = QPushButton('New environment')
        self.addButton.clicked.connect(self.addNewEnvironment)
        lay.addWidget(self.addButton)
        lay.addStretch()
        self.environmentFrame.setLayout(lay)
        scroll.setWidgetResizable(True)
        scroll.setWidget(self.environmentFrame)
        scroll.setMinimumWidth(140)
        scroll.setMinimumHeight(200)

        policy = scroll.sizePolicy()
        policy.setVerticalStretch(1)
        scroll.setSizePolicy(policy)
        layout.addWidget(scroll)

        self.setLayout(layout)

    def addNewEnvironment(self):
        envWidget = EnvironmentWidget(self.inventory, middle = self.middle, parent = self,
                                      show_full_inventory=self.show_full_inventory)
        pos = self.environmentFrame.layout().count() - 2
        self.environmentFrame.layout().insertWidget(pos,envWidget)

    @Slot(list)
    def addCopiedEnvironment(self, args):
        copy_data = args[0] if args else None
        envWidget = EnvironmentWidget(self.inventory, middle=self.middle, parent=self, copy_data=copy_data)
        pos = self.environmentFrame.layout().count() - 2
        self.environmentFrame.layout().insertWidget(pos, envWidget)

    def value(self):
        envs = []
        for ind in range(self.environmentFrame.layout().count() - 2):
            wid = self.environmentFrame.layout().itemAt(ind).widget()
            envs.append(wid.value())
        return envs

    def displayValue(self):
        envs = []
        for ind in range(self.environmentFrame.layout().count() - 2):
            wid = self.environmentFrame.layout().itemAt(ind).widget()
            envs.append(wid.displayValue())
        return envs

class EnvironmentSelectWidget(QGroupBox):
    def __init__(self, inventory, parent = None, middle = True, show_full_inventory=False):
        QGroupBox.__init__(self,'Environments',parent)
        self.parent = parent
        self.middle = middle
        self.inventory = inventory
        self.show_full_inventory = show_full_inventory

        layout = QVBoxLayout()

        scroll = QScrollArea()
        self.environmentFrame = QWidget()
        lay = QBoxLayout(QBoxLayout.TopToBottom)
        self.addButton = QPushButton('New environment')
        self.addButton.clicked.connect(self.addNewEnvironment)
        lay.addWidget(self.addButton)
        lay.addStretch()
        self.environmentFrame.setLayout(lay)
        scroll.setWidgetResizable(True)
        scroll.setWidget(self.environmentFrame)
        scroll.setMinimumWidth(140)
        scroll.setMinimumHeight(200)

        policy = scroll.sizePolicy()
        policy.setVerticalStretch(1)
        scroll.setSizePolicy(policy)
        layout.addWidget(scroll)

        self.setLayout(layout)

    def addNewEnvironment(self):
        envWidget = EnvironmentWidget(self.inventory, middle = self.middle, parent = self,
                                      show_full_inventory=self.show_full_inventory)
        pos = self.environmentFrame.layout().count() - 2
        self.environmentFrame.layout().insertWidget(pos,envWidget)

    @Slot(list)
    def addCopiedEnvironment(self, args):
        copy_data = args[0] if args else None
        envWidget = EnvironmentWidget(self.inventory, middle=self.middle, parent=self, copy_data=copy_data)
        pos = self.environmentFrame.layout().count() - 2
        self.environmentFrame.layout().insertWidget(pos, envWidget)

    def value(self):
        envs = []
        for ind in range(self.environmentFrame.layout().count() - 2):
            wid = self.environmentFrame.layout().itemAt(ind).widget()
            envs.append(wid.value())
        return envs

    def displayValue(self):
        envs = []
        for ind in range(self.environmentFrame.layout().count() - 2):
            wid = self.environmentFrame.layout().itemAt(ind).widget()
            envs.append(wid.displayValue())
        return envs

class EnvironmentWidget(QWidget):
    envCopied = Signal(list)
    def __init__(self, inventory, parent = None, middle = True, copy_data = None, show_full_inventory = False):
        QWidget.__init__(self)#, parent)
        self.inventory = inventory
        self.parent = parent
        self.middle = middle
        self.show_full_inventory = show_full_inventory
        self.envCopied.connect(self.parent.addCopiedEnvironment)
        layout = QHBoxLayout()

        self.lhsAddNew = QPushButton('+')

        self.lhsAddNew.clicked.connect(self.addLhs)

        self.lhsWidget = QWidget()

        lhslayout = QHBoxLayout()
        self.lhsWidget.setLayout(lhslayout)

        self.rhsAddNew = QPushButton('+')

        self.rhsAddNew.clicked.connect(self.addRhs)

        self.rhsWidget = QWidget()

        rhslayout = QHBoxLayout()
        self.rhsWidget.setLayout(rhslayout)

        self.middleWidget = EnvironmentSegmentWidget(self.inventory, middle = True, enabled = middle,
                                                     show_full_inventory=show_full_inventory)

        self.removeButton = QPushButton('Remove environment')
        self.removeButton.clicked.connect(self.deleteLater)
        self.copyButton = QPushButton('Copy environment')
        self.copyButton.clicked.connect(self.copyEnvironment)

        layout.addWidget(self.lhsAddNew)
        layout.addWidget(self.lhsWidget)
        layout.addWidget(self.middleWidget)
        layout.addWidget(self.rhsWidget)
        layout.addWidget(self.rhsAddNew)

        layout.addStretch()

        optionlayout = QVBoxLayout()

        optionlayout.addWidget(self.removeButton)
        optionlayout.addWidget(self.copyButton)

        layout.addLayout(optionlayout)

        self.setLayout(layout)
        if copy_data:
            self.loadfromCopy(copy_data)

    def loadfromCopy(self, copy_data):
        for ind in range(copy_data.lhsWidget.layout().count()):
            copy_wid = copy_data.lhsWidget.layout().itemAt(ind).widget()
            wid = EnvironmentSegmentWidget(self.inventory, preset_label=copy_wid)
            self.lhsWidget.layout().insertWidget(ind, wid)
        for ind in range(copy_data.rhsWidget.layout().count()):
            copy_wid = copy_data.rhsWidget.layout().itemAt(ind).widget()
            wid = EnvironmentSegmentWidget(self.inventory, preset_label=copy_wid)
            self.rhsWidget.layout().insertWidget(ind, wid)
        if self.middle:
            copy_wid = copy_data.middleWidget
            self.middleWidget.mainLabel.setText(copy_wid.mainLabel.text())


    def copyEnvironment(self):
        self.envCopied.emit([self])

    def addLhs(self):
        segWidget = EnvironmentSegmentWidget(self.inventory, show_full_inventory=self.show_full_inventory)
        self.lhsWidget.layout().insertWidget(0,segWidget)

    def addRhs(self):
        segWidget = EnvironmentSegmentWidget(self.inventory, show_full_inventory=self.show_full_inventory)
        self.rhsWidget.layout().addWidget(segWidget)

    def value(self):
        lhs = []
        for ind in range(self.lhsWidget.layout().count()):
            wid = self.lhsWidget.layout().itemAt(ind).widget()
            lhs.append(wid.value())
        rhs = []
        for ind in range(self.rhsWidget.layout().count()):
            wid = self.rhsWidget.layout().itemAt(ind).widget()
            rhs.append(wid.value())
        middle = self.middleWidget.value()

        return EnvironmentFilter(middle, lhs, rhs)

    def displayValue(self):

        lhs = list()
        rhs = list()

        for ind in range(self.lhsWidget.layout().count()):
            wid = self.lhsWidget.layout().itemAt(ind).widget()
            lhs.append(wid.displayValue())
        lhs = ','.join(lhs) if lhs else ''

        for ind in range(self.rhsWidget.layout().count()):
            wid = self.rhsWidget.layout().itemAt(ind).widget()
            rhs.append(wid.displayValue())
        rhs = ','.join(rhs) if rhs else ''

        return '{}_{}'.format(lhs, rhs)

class EnvironmentDialog(QDialog):
    rowToAdd = Signal(str)
    def __init__(self, inventory,parent=None):
        QDialog.__init__(self,parent)

        self.inventory = inventory

        layout = QVBoxLayout()

        layout.setAlignment(Qt.AlignTop | Qt.AlignLeft)

        self.lhsEnvFrame = QGroupBox('Left hand side')

        self.rhsEnvFrame = QGroupBox('Right hand side')

        lhsEnvLayout = QVBoxLayout()

        lhsEnvLayout.setAlignment(Qt.AlignTop | Qt.AlignLeft)

        rhsEnvLayout = QVBoxLayout()

        rhsEnvLayout.setAlignment(Qt.AlignTop | Qt.AlignLeft)

        self.lhs = SegmentSelectionWidget(self.inventory, exclusive = True)

        self.rhs = SegmentSelectionWidget(self.inventory, exclusive = True)

        lhsEnvLayout.addWidget(self.lhs)
        rhsEnvLayout.addWidget(self.rhs)

        self.lhsEnvFrame.setLayout(lhsEnvLayout)

        self.rhsEnvFrame.setLayout(rhsEnvLayout)
        envFrame = QFrame()

        envLayout = QHBoxLayout()

        envLayout.addWidget(self.lhsEnvFrame)
        envLayout.addWidget(self.rhsEnvFrame)

        envFrame.setLayout(envLayout)

        layout.addWidget(envFrame)

        self.oneButton = QPushButton('Add')
        self.anotherButton = QPushButton('Add and create another')
        self.cancelButton = QPushButton('Cancel')
        self.acLayout = QHBoxLayout()
        self.acLayout.addWidget(self.oneButton, alignment = Qt.AlignLeft)
        self.acLayout.addWidget(self.anotherButton, alignment = Qt.AlignLeft)
        self.acLayout.addWidget(self.cancelButton, alignment = Qt.AlignLeft)
        self.oneButton.clicked.connect(self.one)
        self.anotherButton.clicked.connect(self.another)
        self.cancelButton.clicked.connect(self.reject)

        acFrame = QFrame()
        acFrame.setLayout(self.acLayout)

        layout.addWidget(acFrame, alignment = Qt.AlignLeft)
        self.addOneMore = False
        self.setLayout(layout)
        #self.setFixedSize(self.sizeHint())
        self.setWindowTitle('Create bigram')

    def one(self):
        self.addOneMore = False
        self.accept()

    def another(self):
        self.addOneMore = True
        self.accept()

    def reset(self):
        self.lhs.clearAll()
        self.rhs.clearAll()

    def accept(self):
        lhs = self.lhs.value()
        rhs = self.rhs.value()

        if lhs == '':
            reply = QMessageBox.critical(self,
                    "Missing information", "Please specify a left hand of the bigram.")
            return
        if rhs == '':
            reply = QMessageBox.critical(self,
                    "Missing information", "Please specify a right hand of the bigram.")
            return

        env = lhs, rhs
        self.rowToAdd.emit([env])
        if not self.addOneMore:
            QDialog.accept(self)
        else:
            self.reset()