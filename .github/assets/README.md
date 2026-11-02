# README görselleri

**Güncellendi:** 2026-11-02. Bu dosyalar yalnız GitHub tanıtım yüzeyi içindir; runtime bağımlılığı, benchmark veya uzak EVREN kabul kanıtı değildir. Genel depo lisansı olan MIT kapsamındadır.

| Dosya | Amaç |
|---|---|
| `yorunge-hero.svg` | Özgün, düzenlenebilir vektör kapak; dış kaynak veya script içermez |
| `dataset-demo.gif` | Altı kare, toplam 8,8 saniye; döngü uzantısı yok, son karede durur |
| `dataset-demo.svg` | Tam akışın durağan, düzenlenebilir sürümü |
| `dataset-demo-compact.svg` | Dar ekranlarda okunabilen kısa, durağan akış |
| `dataset-demo.json` | Gerçek komutlardan seçilmiş çıktı, sentetik fixture ve gösterim sırası |

Demo, `015300e` checkout’undaki gerçek CLI çağrılarından hazırlandı: `abc` içeren tek dosya üç byte olarak incelendi; ilk verify exit 0, `xyz` değişiminden sonraki verify exit 7 verdi. Yalnız sentetik yerel dosyalar kullanıldı; ağ, hesap ve anahtar yoktur. Gösterim bir ekran kaydı değildir: komutun executable yolu `yorunge` olarak kısaltıldı; GIF/tam durağan sürümde metin satırları ve exit değerleri kayıttan seçildi. Dar ekran çizimi aynı sonucun kısa özetidir. İşlem süresi veya performans iddiası yoktur. JSON tam stdout/kişisel yol taşımaz; seçilmiş satırları ve kurguyu saklar.

SVG dosyaları doğrudan düzenlenebilir; haricî font veya resim yüklemez. GIF, Pillow 12.0.0 ile bu altı adımın çiziminden üretildi; raster metin için yerel Menlo/Avenir Next kullanıldı, font dosyaları dağıtılmaz. CLI metinleri değişirse aynı sentetik senaryoyu yeniden çalıştırıp JSON, GIF ve iki durağan sürümü birlikte güncelleyin; gerçek çıktıymış gibi yeni satır uydurmayın.

README, hareket azaltma tercihinde tam durağan sürümü, dar ekranda kısa durağan sürümü ister; diğer ekranlarda tek geçişli GIF gösterir. Ayrıca kullanıcı animasyon bölümünü kapatabilir ve durağan dosyayı doğrudan açabilir. Anlam yalnız renkle verilmez; metin ve exit kodu birlikte gösterilir. Dosyalar yalnız Git checkout’unda tutulur; wheel/sdist girdisi değildir.
