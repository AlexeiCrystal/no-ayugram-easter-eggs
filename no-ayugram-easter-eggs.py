__id__ = "no_ayugram_easter_eggs"
__name__ = "🛡No AyuGram Easter Eggs🥚"
__version__ = "1.1"
__min_version__ = "11.12.0"
__app_version__ = ">=11.12.0"
__sdk_version__ = ">=1.4.3.3"
__author__ = "@ayugram_easter"
__icon__ = "AllTheMemes/0"
__description__ = """
🇬🇧**EN:** The plugin protects against opening AyuGram Easter eggs (tg://ayu/... train, xiaomi, relax, augh, pipe, saul, komaru, lobster)
/
🇷🇺**RU:** Плагин защищает от открытия пасхалок AyuGram (tg://ayu/... train, xiaomi, relax, augh, pipe, saul, komaru, lobster)
"""

import traceback
from base_plugin import BasePlugin, MethodReplacement
from hook_utils import find_class
from client_utils import get_last_fragment
from ui.alert import AlertDialogBuilder
from android_utils import run_on_ui_thread, log
from ui.settings import Header, Text, Switch
from java.util import Locale

TARGET_PATHS = {
    "tg://ayu/train",
    "tg://ayu/xiaomi",
    "tg://ayu/relax",
    "tg://ayu/augh",
    "tg://ayu/pipe",
    "tg://ayu/saul",
    "tg://ayu/komaru",
    "tg://ayu/lobster",
    "tg://xiaomi",
    "tg://nya"
}

HANDLER_CLASSES = (
    "com.radolyn.ayugram.AyuInAppHandlers",
    "com.radolyn.ayugram.utils.AyuInAppHandlers",
)

AYU_ROFLS_CORE_CLASS = "com.extera.plugins.ayurofls.AyuRoflsCore"

HANDLER_METHODS = (
    "handleAyu",
    "handleXiaomi",
    "handleNekogram",
)

GITHUB_URL = "https://github.com/AlexeiCrystal/no-ayugram-easter-eggs"

LOCALIZED = {
    "ru": {
        "settings_header": "Настройки",
        "show_dialog": "Показывать диалог",
        "show_dialog_sub": "При включении будет показываться предупреждение при попытке открыть пасхалку",
        "links_header": "Ссылки",
        "open_github": "Открыть GitHub",
        "dialog_message": "Заблокировано открытие пасхалки:\n{url}",
        "dialog_message_no_url": "Заблокировано открытие пасхалки",
        "close": "Закрыть",
        "git_dialog_title": "GitHub",
        "git_dialog_ok": "OK"
    },
    "en": {
        "settings_header": "Settings",
        "show_dialog": "Show dialog",
        "show_dialog_sub": "When enabled, a warning will be shown when trying to open an easter egg",
        "links_header": "Links",
        "open_github": "Open GitHub repository",
        "dialog_message": "Blocked opening of easter egg:\n{url}",
        "dialog_message_no_url": "Blocked opening of easter egg",
        "close": "Close",
        "git_dialog_title": "GitHub",
        "git_dialog_ok": "OK"
    }
}

def _get_lang():
    try:
        if Locale:
            lang = Locale.getDefault().getLanguage()
            return "ru" if str(lang).lower().startswith("ru") else "en"
    except Exception:
        pass
    return "en"

def _t(key: str, **kwargs) -> str:
    lang = _get_lang()
    block = LOCALIZED.get(lang, LOCALIZED["en"])
    text = block.get(key, LOCALIZED["en"].get(key, ""))
    try:
        return text.format(**kwargs)
    except Exception:
        return text

class NoOpReplacement(MethodReplacement):
    def __init__(self, plugin):
        self.plugin = plugin
    
    def replace_hooked_method(self, param):
        show_dialog = self.plugin.get_setting("show_dialog", True)
        if show_dialog:
            run_on_ui_thread(lambda: self.plugin.show_block_dialog_no_url())
        return None

class _DeepLinkHookAyu:
    def __init__(self, plugin):
        self.plugin = plugin
        self.pending_param = None

    def before_hooked_method(self, param):
        try:
            intent = param.args[0]
            if not intent or not intent.getData():
                return
            url = str(intent.getData())
            
            if not url.startswith("tg://"):
                return
            
            blocked = False
            
            if url == "tg://ayu" or url == "tg://ayu/":
                blocked = True
            
            if not blocked:
                for target in TARGET_PATHS:
                    if url.startswith(target):
                        blocked = True
                        break
            
            if blocked:
                self.pending_param = param
                param.setResult(None)
                
                show_dialog = self.plugin.get_setting("show_dialog", True)
                if show_dialog:
                    run_on_ui_thread(lambda: self.plugin.show_block_dialog_with_url(url))
                else:
                    self.close_dialog()
                    
        except Exception:
            self.plugin.log("DeepLinkHook error: " + traceback.format_exc())

    def close_dialog(self):
        self.pending_param = None

class AntiAyuPlugin(BasePlugin):
    def __init__(self):
        super().__init__()
        self.unhook_deeplink = None
        self._unhooks = []

    def on_plugin_load(self):
        self.log("No AyuGram Easter Eggs loaded.")
        self._setup_deeplink_hook()
        self._disable_ayu_rofls_plugin()
        self._hook_ayu_handlers()

    def on_plugin_unload(self):
        if self.unhook_deeplink:
            try:
                self.unhook_method(self.unhook_deeplink)
            except Exception:
                pass
            self.unhook_deeplink = None
        
        for unhook in list(self._unhooks):
            try:
                self.unhook_method(unhook)
            except Exception:
                pass
        self._unhooks.clear()
        
        self.log("No AyuGram Easter Eggs unloaded.")

    def show_block_dialog_with_url(self, url):
        fragment = get_last_fragment()
        activity = fragment.getParentActivity() if fragment else None
        if not activity:
            return

        try:
            builder = AlertDialogBuilder(activity)
            builder.set_title(__name__)
            builder.set_message(_t("dialog_message", url=url))
            builder.set_positive_button(_t("close"), None)
            builder.show()
        except Exception:
            self.log("Failed to show dialog: " + traceback.format_exc())

    def show_block_dialog_no_url(self):
        fragment = get_last_fragment()
        activity = fragment.getParentActivity() if fragment else None
        if not activity:
            return

        try:
            builder = AlertDialogBuilder(activity)
            builder.set_title(__name__)
            builder.set_message(_t("dialog_message_no_url"))
            builder.set_positive_button(_t("close"), None)
            builder.show()
        except Exception:
            self.log("Failed to show dialog: " + traceback.format_exc())

    def _setup_deeplink_hook(self):
        try:
            launch_activity_cls = find_class("org.telegram.ui.LaunchActivity")
            method = launch_activity_cls.getClass().getDeclaredMethod(
                "handleIntent",
                find_class("android.content.Intent"),
                find_class("java.lang.Boolean").TYPE,
                find_class("java.lang.Boolean").TYPE,
                find_class("java.lang.Boolean").TYPE,
                find_class("org.telegram.messenger.browser.Browser$Progress"),
                find_class("java.lang.Boolean").TYPE,
                find_class("java.lang.Boolean").TYPE
            )
            self.unhook_deeplink = self.hook_method(method, _DeepLinkHookAyu(self))
        except Exception:
            try:
                metod2 = launch_activity_cls.getClass().getDeclaredMethod("handleIntent", find_class("android.content.Intent"))
                self.unhook_deeplink = self.hook_method(metod2, _DeepLinkHookAyu(self))
            except Exception:
                self.log("Failed to hook LaunchActivity.handleIntent for Ayu links.")

    def _disable_ayu_rofls_plugin(self):
        clazz = find_class(AYU_ROFLS_CORE_CLASS)
        if clazz is None:
            return

        try:
            method = clazz.getDeclaredMethod("unload")
            method.setAccessible(True)
            method.invoke(None)
            self.log("AyuRoflsCore unloaded successfully")
        except Exception as exc:
            self.log(f"AyuRoflsCore.unload failed: {exc}")

        self._unhooks.extend(
            self.hook_all_methods(
                clazz,
                "load",
                NoOpReplacement(self),
                priority=10000,
            ) or []
        )

    def _hook_ayu_handlers(self):
        for class_name in HANDLER_CLASSES:
            clazz = find_class(class_name)
            if clazz is None:
                continue
            for method_name in HANDLER_METHODS:
                self._unhooks.extend(
                    self.hook_all_methods(
                        clazz,
                        method_name,
                        NoOpReplacement(self),
                        priority=10000,
                    ) or []
                )
        self.log("Ayu handlers hooked successfully")

    def _on_show_dialog_change(self, key: str, value: bool):
        self.log(f"Show dialog setting changed to: {value}")
        current_value = self.get_setting(key, True)
        self.set_setting(key, not current_value, reload_settings=True)

    def create_settings(self):
        items = []
        
        try:
            if Header:
                items.append(Header(text=_t("settings_header")))
        except Exception:
            pass
        
        try:
            if Switch:
                items.append(Switch(
                    key="show_dialog",
                    text=_t("show_dialog"),
                    default=True,
                    subtext=_t("show_dialog_sub"),
                    icon="msg_info",
                    on_change=self._on_show_dialog_change,
                    link_alias="show_dialog",
                ))
        except Exception:
            pass
        
        try:
            if Header:
                items.append(Header(text=_t("links_header")))
        except Exception:
            pass

        def open_github(v):
            try:
                fragment = get_last_fragment()
                activity = fragment.getParentActivity() if fragment else None
                if not activity:
                    return
                try:
                    from org.telegram.messenger.browser import Browser
                    from android.net import Uri
                    Browser.openUrl(activity, Uri.parse(GITHUB_URL))
                except Exception:
                    b = AlertDialogBuilder(activity)
                    b.set_title(_t("git_dialog_title"))
                    b.set_message(GITHUB_URL)
                    b.set_positive_button(_t("git_dialog_ok"), None)
                    b.show()
            except Exception:
                self.log("Failed to open GitHub: " + traceback.format_exc())

        try:
            if Text:
                items.append(Text(text=_t("open_github"), on_click=open_github, icon="msg_link", link_alias="open_github"))
        except Exception:
            pass

        return items

    def log(self, message: str):
        log(f"[No AyuGram Easter Eggs] {message}")