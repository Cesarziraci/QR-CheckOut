import kivy
import gspread
from PIL import Image
from datetime import date
from time import ctime, gmtime
from pyzbar.pyzbar import decode
from oauth2client.service_account import ServiceAccountCredentials

kivy.require('2.0.0')
from kivy.app import App
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.popup import Popup
from kivy.clock import Clock
from kivy.lang import Builder
from kivy.uix.screenmanager import Screen, ScreenManager


scope = [
	"https://spreadsheets.google.com/feeds",
	"https://www.googleapis.com/auth/spreadsheets",
	"https://www.googleapis.com/auth/drive.file",
	"https://www.googleapis.com/auth/drive"
]

creds = ServiceAccountCredentials.from_json_keyfile_name("sigit-apps-cc25c0f862ec.json", scope)
client = gspread.authorize(creds)
s = client.open('CheckIn_Fabrica')

Builder.load_string('''
<CameraScreen>:
    BoxLayout:
        orientation: 'vertical'    
        Camera:
            id: camera
            resolution: (640, 480)
            play: False
            canvas.before:
                Rotate:
                    angle: -90
                    origin: self.center	       
<MainScreen>:
	GridLayout:
		cols:1
		rows:8
		padding: 10
		spacing: 5
		canvas:
			Color: 
				rgb: 1, 1, 1
			Rectangle:
				size: self.size
				pos: self.pos

		Image: 
			source: 'SIGIT.jpg'
			size_hint_x: 0.21
			allow_stretch: True

		Label: 
			text: 'CheckOut fabrica'
			color: 0,0,0
			size_hint: .5, .95
			font_size: 50
			markup: True
			bold: True

		ToggleButton:
			text: 'Abrir Escaner'
			on_press: root.open_camera()
			height: '48dp'
			size_hint: .5, .95
			pos_hint: {"center_x": .5, "center_y": .5}
			bold: True
			font_size: 50		    

        Label: 
            text: 'Nombre y apellidos: '
            color: 0,0,0
            size_hint: .5, .85
            font_size: 40
            markup: True
            size: self.texture_size
            bold: True

        TextInput:
            id: name
            pos_hint: {'center_x': 0.5, 'center_y': 0.705}
            size_hint: .5, .85
            focus: True
            multiline: False
		    
		ToggleButton:
			id: guardar
			text: 'Abrir/Cerrar'
			on_press: root.switch()
			height: '48dp'
			size_hint: .5, .95
			pos_hint: {"center_x": .5, "center_y": .5}
			bold: True
			font_size: 50

<ScreenManager>:
	MainScreen:
	CameraScreen:

''')

class MainScreen(Screen):
	qr_model = ''

	def open_camera(self):
		self.manager.current = 'camera'

	def set_qr_model(self, qr_code_data):
		self.qr_model = qr_code_data
		Aviso_pop(self.qr_model)

	def switch(self):
		if self.qr_model == '':
			error("Escanea primero un QR")
		elif self.ids.name.text == '':
			error("Introduce tu nombre")
		else:
			Guardar_datos(self.qr_model,self.ids.name.text)

def buscar_vacia(sheet):
	j = 1
	for i in sheet.col_values(1):
		j = j + 1
		if sheet.cell(j,1).value is None:
			return j

def Guardar_datos(qr_model, name):
	layout = GridLayout(cols=1, padding=10)
	popup = Popup(title="Guardar",
				content=layout,
				size_hint=(.5, .5))

	sheet1 = s.worksheet("Hoja 1")
	
	try:
		Model = sheet1.find(qr_model)
		state = sheet1.cell(Model.row, Model.col+1).value

		popupLabel = Label(text="La {} esta {} ".format(qr_model, state.lower()))
		
		match state:
			case 'ABIERTO':
				text='Cerrar'
			case 'CERRADO':
				text = 'Abrir'
			case 'ENCENDIDO':
				text = 'Apagar'
			case 'APAGADO':
				text = 'Encender'

		switchbutton = Button(text=text, size_hint=(.4, .4))

		layout.add_widget(popupLabel)
		layout.add_widget(switchbutton)

		popup.open()

		switchbutton.bind(on_press= lambda x:datos(qr_model, name, state))
		switchbutton.bind(on_press=popup.dismiss)
	except AttributeError:
		error("No se encontro esta ubicacion en la base de datos \n avisa al responsable", "Error")
	
def datos(qr_model, name, state):
	sheet1 = s.worksheet("Hoja 1")
	try:
		Time = ''
		Time = ctime()
		Model = sheet1.find(qr_model)
		Time_find = sheet1.find("Fecha Ultima Mod")
		Name_find = sheet1.find("Ultima Persona en Modificar")
		sheet1.update_cell(Time_find.row+1,Time_find.col, Time)
		sheet1.update_cell(Name_find.row+1, Name_find.col, name)

		match state:
			case 'ABIERTO':
				text = 'CERRADO'
			case 'CERRADO':
				text = 'ABIERTO'
			case 'ENCENDIDO':
				text = 'APAGADO'
			case 'APAGADO':
				text = 'ENCENDIDO'

		sheet1.update_cell(Model.row, Model.col + 1, text)
		Aviso_pop(text.lower())
		
		qr_model = ' '

	except (ValueError, NameError, TypeError):
		error("Error! Avisar al encargado", "Error")

def error(text, tittle):
    layout = GridLayout(cols=1, padding=10)
    popup = Popup(title=tittle,
                 content=layout,
                 size_hint=(.5, .5))

    popupLabel = Label(text=text)
    closeButton = Button(text="Cerrar", size_hint=(.3, .3))

    layout.add_widget(popupLabel)
    layout.add_widget(closeButton)
    
    closeButton.bind(on_oress = popup.dismiss)
    popup.open()


    closeButton.bind(on_press=popup.dismiss)

class CameraScreen(Screen):
	camera_active = False
	qr_detected = False

	def on_enter(self):
		self.camera = self.ids.camera
		self.qr_detected = False
		self.camera.play = True
		Clock.schedule_interval(self.decode_qr, 1 / 30)
		self.camera_active = True

	def on_leave(self):
		if self.camera is not None:
			self.camera.play = False
			Clock.unschedule(self.decode_qr)
			self.camera_active = False

	def close_camera(self):
		self.manager.current = 'Main'

	def decode_qr(self, dt):
		image_data = self.camera.texture.pixels
		width, height = self.camera.resolution
		image = Image.frombytes(mode='RGBA', size=(width, height), data=image_data)
		image_flip = image.transpose(Image.FLIP_LEFT_RIGHT)
		decoded_qr_codes = decode(image_flip)

		if not self.qr_detected and len(decoded_qr_codes) > 0:
			qr_code_data = decoded_qr_codes[0].data.decode('utf-8')
			mainscreen = self.manager.get_screen('Main')
			mainscreen.set_qr_model(qr_code_data)
			self.qr_detected = True
			self.manager.current = 'Main'

class mainApp(App):
	title = "Sigit-CheckOut"
	def build(self):
		sm = ScreenManager()
		sm.add_widget(MainScreen(name='Main'))
		sm.add_widget(CameraScreen(name='camera'))
		return sm

if __name__ == '__main__':
	mainApp().run()
