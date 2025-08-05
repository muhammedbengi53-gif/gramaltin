import io
import base64
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.camera import Camera
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.uix.popup import Popup
from kivy.utils import platform
import requests
import json
from PIL import Image
import threading

class CameraApp(App):
    def __init__(self):
        super().__init__()
        self.camera = None
        self.answer_label = None
        
        # Google Gemini API anahtarınızı buraya ekleyin
        self.GEMINI_API_KEY = "AIzaSyAAFbj9k5um9RN53eH2xdvfC2vDNj3Ux9s"
        self.GEMINI_API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={self.GEMINI_API_KEY}"

    def build(self):
        # Ana layout
        main_layout = BoxLayout(orientation='vertical', padding=10, spacing=10)
        
        # Kamera widget'ı
        if platform == 'android':
            # Android için kamera ayarları
            self.camera = Camera(play=True, resolution=(640, 480), index=0)
        else:
            # Masaüstü test için
            self.camera = Camera(play=True, resolution=(640, 480))
        
        main_layout.add_widget(self.camera)
        
        # Başla butonu
        start_button = Button(
            text='BAŞLA',
            size_hint=(1, 0.15),
            font_size='20sp',
            background_color=(0.2, 0.6, 1, 1)
        )
        start_button.bind(on_press=self.capture_and_analyze)
        main_layout.add_widget(start_button)
        
        # Cevap label'ı
        self.answer_label = Label(
            text='Kamerayı soruya doğrultun ve BAŞLA butonuna basın',
            size_hint=(1, 0.3),
            text_size=(None, None),
            halign='center',
            valign='middle',
            font_size='16sp'
        )
        main_layout.add_widget(self.answer_label)
        
        return main_layout

    def capture_and_analyze(self, instance):
        """Fotoğraf çek ve analiz et"""
        try:
            # Loading mesajı göster
            self.answer_label.text = "Fotoğraf çekiliyor ve analiz ediliyor..."
            
            # Fotoğraf çek
            self.camera.export_to_png("temp_image.png")
            
            # Analizi thread'de çalıştır (UI donmaması için)
            thread = threading.Thread(target=self.analyze_image)
            thread.daemon = True
            thread.start()
            
        except Exception as e:
            self.show_error(f"Fotoğraf çekerken hata: {str(e)}")

    def analyze_image(self):
        """Görüntüyü Gemini API ile analiz et"""
        try:
            # Görüntüyü base64'e çevir
            image_base64 = self.image_to_base64("temp_image.png")
            
            # Gemini API isteği hazırla
            payload = {
                "contents": [
                    {
                        "parts": [
                            {
                                "text": "Bu görüntüdeki matematik, fen, edebiyat veya diğer akademik soruyu analiz et ve çöz. Sadece sorunun cevabını ver, açıklama yapma. Eğer görüntüde soru yoksa 'Görüntüde soru bulunamadı' yaz."
                            },
                            {
                                "inline_data": {
                                    "mime_type": "image/png",
                                    "data": image_base64
                                }
                            }
                        ]
                    }
                ]
            }
            
            # API isteği gönder
            headers = {
                "Content-Type": "application/json"
            }
            
            response = requests.post(
                self.GEMINI_API_URL,
                headers=headers,
                data=json.dumps(payload),
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                
                # Cevabı al
                if 'candidates' in result and len(result['candidates']) > 0:
                    answer = result['candidates'][0]['content']['parts'][0]['text']
                    # UI thread'de cevabı göster
                    Clock.schedule_once(lambda dt: self.show_answer(answer), 0)
                else:
                    Clock.schedule_once(lambda dt: self.show_error("API'dan cevap alınamadı"), 0)
            else:
                Clock.schedule_once(lambda dt: self.show_error(f"API Hatası: {response.status_code}"), 0)
                
        except requests.exceptions.Timeout:
            Clock.schedule_once(lambda dt: self.show_error("İstek zaman aşımına uğradı"), 0)
        except requests.exceptions.ConnectionError:
            Clock.schedule_once(lambda dt: self.show_error("İnternet bağlantısı hatası"), 0)
        except Exception as e:
            Clock.schedule_once(lambda dt: self.show_error(f"Analiz hatası: {str(e)}"), 0)

    def image_to_base64(self, image_path):
        """Görüntüyü base64 formatına çevir"""
        try:
            # PIL ile görüntüyü aç ve optimize et
            with Image.open(image_path) as img:
                # Görüntüyü küçült (API limitleri için)
                img.thumbnail((800, 800), Image.Resampling.LANCZOS)
                
                # RGB formatına çevir
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                
                # Base64'e çevir
                buffered = io.BytesIO()
                img.save(buffered, format="PNG")
                img_base64 = base64.b64encode(buffered.getvalue()).decode()
                
                return img_base64
                
        except Exception as e:
            raise Exception(f"Görüntü işleme hatası: {str(e)}")

    def show_answer(self, answer):
        """Cevabı göster"""
        self.answer_label.text = f"CEVAP:\n\n{answer}"
        self.answer_label.text_size = (Window.width - 20, None)

    def show_error(self, error_message):
        """Hata mesajı göster"""
        self.answer_label.text = f"HATA: {error_message}"
        
        # Popup ile de göster
        popup = Popup(
            title='Hata',
            content=Label(text=error_message),
            size_hint=(0.8, 0.4)
        )
        popup.open()

    def on_start(self):
        """Uygulama başladığında çalışır"""
        if platform == 'android':
            # Android izinlerini kontrol et
            from android.permissions import request_permissions, Permission
            request_permissions([
                Permission.CAMERA,
                Permission.WRITE_EXTERNAL_STORAGE,
                Permission.READ_EXTERNAL_STORAGE,
                Permission.INTERNET
            ])

# Uygulamayı çalıştır
if __name__ == '__main__':
    CameraApp().run()