# İçme Suyu Kalitesi – Bulanık Mantık Dönem Projesi

Ders: Bulanık Mantık | Dönem: 2025-2026 | Teslim: 21.05.2026

9 fizikokimyasal parametre -> 3 ara model -> 1 final skor (0-100%)

---

## Hızlı Başlangıç

```bash
pip install -r requirements.txt
streamlit run app.py
```

Tarayıcıda http://localhost:8501 açılır.

Komut satırı batch analizi için:
```bash
python water_quality_fis.py
```

---

## Model Mimarisi

```
Sertlik    ─┐
pH         ─┼─► FWQ1 (SK1) ─┐
Alkalinite ─┘               │
                             ├─► Final Su Kalitesi (0-100%)
Ca ─┐                        │
Mg ─┼─► FWQ2 (SK2) ──────────┤
Fe ─┘                        │
                             │
Sulfat  ─┐                   │
Nitrat  ─┼─► FWQ3 (SK3) ────┘
Florur  ─┘
```

| Model | Girişler              | Çıkış        |
|-------|-----------------------|--------------|
| FWQ1  | Sertlik, pH, Alkalinite | SK1 (0-100%) |
| FWQ2  | Ca, Mg, Fe            | SK2 (0-100%) |
| FWQ3  | Sülfat, Nitrat, Florür | SK3 (0-100%) |
| Final | SK1, SK2, SK3         | Son Su Kalitesi |

---

## Sistem Özellikleri

| Özellik             | Detay                              |
|---------------------|------------------------------------|
| Çıkarım yöntemi     | Mamdani (min-maks)                 |
| Üyelik fonksiyonu   | Üçgen (Triangular MF)              |
| Durulaştırma        | Centroid (Ağırlık Merkezi)         |
| Giriş MF sınıfları  | Düşük / Orta / Yüksek              |
| Çıkış MF sınıfları  | 7 sınıf (ÇÇD → ÇÇY)              |
| Toplam kural sayısı | 112 kural (27x3 ara + 31 final)    |

---

## Arayüz Özellikleri (Streamlit)

- 9 slider – tüm parametreler için anlık giriş
- Üyelik fonksiyon grafikleri – 9 giriş + 4 çıkış
- Aktif kural listesi – ateşlenen kurallar aktivasyon sıralı tablo
- Centroid durulaştırma – sayısal + grafiksel çıktı
- Gauge göstergesi – SK1/SK2/SK3/Final anlık görsel
- Sıfırlama butonu

---

## Dosya Yapısı

```
├── app.py                                  # Streamlit arayüzü (ana uygulama)
├── water_quality_fis.py                    # Komut satırı + grafik üretimi
├── requirements.txt                        # Python bağımlılıkları
├── README.md                               # Bu dosya
└── Su_Kalitesi_Bulanik_Mantik_Raporu.docx  # Türkçe proje raporu
```

---

## Test Sonuçları

| Model         | Bu Çalışma (Python) |
|---------------|---------------------|
| SK1 Fiziksel  | 87.9%               |
| SK2 Mineral   | 93.5%               |
| SK3 Kimyasal  | 94.4% (eslesme)     |
| Final         | 84.3%               |

