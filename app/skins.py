from kivy.clock import Clock, mainthread
from kivy.uix.gridlayout import GridLayout
from kivy.uix.progressbar import ProgressBar
from kivy.uix.label import Label
from kivy.uix.button import Button

from api.skins import Skins


class SkinWidget(GridLayout):

    def __init__(self, obj, **kwargs):
        self.obj = obj
        self.obj.set_progress_bar_clbk(self.update_progress_bar)

        self.cols = 4
        self.orientation = 'tb-lr'
        self.size_hint = (1, None)
        self.height = 50
        super(SkinWidget, self).__init__(**kwargs)

        self.download_btn = Button(text='Download', size=(150, 30), color=[1,1,1,1], size_hint=(None, None), padding_x=(10, 10))
        self.add_widget(self.download_btn)
        self.download_btn.bind(on_press=self.click)

        self.add_widget(Label(text=self.obj.file, size=(450, 30), size_hint=(None, None)))
        self.lb = Label(text="0%", size=(50, 30), size_hint=(None, None))
        self.add_widget(self.lb)
        self.pb = ProgressBar(max=100, size=(300, 30), size_hint=(None, None))
        self.add_widget(self.pb)
        

    def click(self, instance):
        instance.disabled = True
        self.obj.download()

    @mainthread
    def update_progress_bar(self, current_size, max_size):
        percent = int(current_size * 100 / max_size)
        self.pb.value = percent
        self.lb.text = "{}%".format(percent)
        
        # TODO: it's very optimistic, must be changed
        if percent >= 100:
            self.download_btn.disabled = False


class SkinsView(GridLayout):

    def __init__(self, config, **kwargs):
        super(SkinsView, self).__init__(**kwargs)
        self.skins_api = Skins(config.get('ac', 'address'), config.get('ac', 'skins_destination'))
        self.skin_widgets = []

        download_all_btn = self.ids.download_all
        download_all_btn.bind(on_press=self.click)

        content = self.ids.content
        content.bind(minimum_height=content.setter('height'))
        for _, obj in self.skins_api.list().items():
            widget = SkinWidget(obj)
            self.skin_widgets.append(widget)
            content.add_widget(widget)
    
    def click(self, instance):
        for skin in self.skin_widgets:
            skin.download_btn.trigger_action()
