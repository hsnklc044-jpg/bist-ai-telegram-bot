# Nakit getirisi verileri

Backtest'te boşta kalan nakdin getirisi bu klasördeki CSV dosyalarından okunur
(`core/backtest/cash.py`). Her satırda **kaynak** zorunludur; kaynaksız satır
reddedilir. Eksik dönem tahminle doldurulmaz, raporda "eksik gün" olarak sayılır.

| Dosya | Sütunlar | Not |
| --- | --- | --- |
| `policy_rate.csv` | `effective_date, rate, source` | TCMB politika faizi. `effective_date` = kararın açıklandığı günden **sonraki** işlem günü. Yalnız üst sınır duyarlılığı için. |
| `deposit_rate.csv` | `effective_date, rate, source` | TCMB EVDS ağırlıklı ortalama TL mevduat faizi (1 aya kadar). `effective_date` = **yayım** tarihi. |
| `ppf_<KOD>.csv` | `date, price, source` | Para piyasası fonunun TEFAS birim fiyatı. Önerilen birincil seri. |
| `withholding.csv` | `effective_date, rate, source` | Stopaj oranı (0.15 = %15), yürürlük tarihiyle. |

Oranlar ondalık yazılır: %45 → `0.45`. Biçim örneği (uydurma değerlerle):

```
effective_date,rate,source
2000-01-03,0.10,ÖRNEK SATIR - gerçek değer değil
```

Kullanım:

```
python -m core.backtest.research --cash fund:data/cash/ppf_XXX.csv,tax=data/cash/withholding.csv
python -m core.backtest.research --cash fixed:0.35
```
