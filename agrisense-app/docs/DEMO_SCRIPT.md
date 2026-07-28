# Demo script — 4 minutes

Rehearse this end to end at least once before presenting. Have the app already
running and the browser on the dashboard before you start talking.

**Pre-flight**
- `python -m uvicorn app.main:app --port 8000` and `npm run dev` both up
- Dashboard loaded once already (warms the weather cache — the app then works
  even if venue wifi dies mid-demo)
- Browser zoom at 100%, dark mode on

---

## 0:00 — The problem (30s)

> "Soil salinisation degrades about 1.5 million hectares of cropland every year.
> The cruel part is that it's invisible until it's expensive — by the time you can
> see salt stress in the crop, the yield is already gone.
>
> And it isn't caused by any one thing a farmer can look at. Salt doesn't
> evaporate. Water leaves the root zone as vapour and the salt it carried stays
> behind. So every irrigation *adds* salt, and only water that drains below the
> roots takes it away. If your drainage is poor, or the water table is shallow and
> saline, your field salinises no matter how carefully you water it."

## 0:30 — The dashboard (45s)

Point at the KPI row, then the field grid.

> "Nine plots across Punjab, Haryana and coastal Gujarat. Three are critical.
>
> Notice the cards lead with the *action*, not the measurement. 'ECe 9.6' means
> nothing to a farmer. 'Leach salt now — 79% yield at risk' is what makes someone
> walk out to the field."

Point at the risk distribution rail.

> "These are the USDA salinity classes, and every risk state carries an icon and a
> label as well as a colour — so it still works if you're colour-blind, or if the
> projector washes out."

## 1:15 — A field in trouble (75s)

Click **Canal Side Paddy**.

> "Rice, irrigated with brackish tubewell water, over a water table 1.6 metres
> down. Rice is one of the most salt-sensitive crops there is — it starts losing
> yield at 3 dS/m."

Point at the salinity chart.

> "Ninety days of measured salinity, then the 30-day forecast. The red line is the
> tolerance threshold for rice. This field is at 9.6 and climbing — three times
> what the crop can take."

Point at the recommendation panel.

> "So the tool doesn't just say 'high salinity'. It computes a leaching depth from
> the FAO-29 leaching curves — apply this many millimetres of low-salinity water,
> split over two to three days because it's clay soil and otherwise it runs off.
>
> And look at the second one: it's telling the farmer to *hold* irrigation because
> 65 mm of rain is coming. Rain is salt-free, so it leaches for you. Advice that
> ignores the forecast wastes water and adds salt."

Point at "What drives this forecast".

> "And the model shows its working — the top features behind this prediction."

## 2:30 — The simulator (60s)

Click **Simulate**. Drag *irrigation water salinity* down to ~0.4, set depth ~70 mm.
Hit **Run simulation**.

> "This is the part I think matters most. A dashboard tells you what's happening.
> A farmer's actual question is 'what if I did something different?'
>
> Here I'm switching from the brackish tubewell to canal water. Same field, same
> weather, same physics engine — the only thing that changed is the lever."

Point at the two curves and the summary line.

> "Salinity ends 1.25 dS/m lower and crop health is 15 points better. It also tells
> you honestly that this *still* doesn't get the field under rice's tolerance —
> which is the real answer. Reclamation takes seasons, and the tool says so rather
> than overselling."

## 3:30 — Honesty and the model (30s)

Click **Model**.

> "Last thing, and it's the part I'd want to be asked about. These models are
> trained on physics-simulated data, not field measurements — there's no public
> dataset that pairs salinity time series with weather at field scale. We say that
> on every screen, not in a footnote.
>
> What we *can* defend is the method. The simulator is FAO-56 and Maas-Hoffman —
> the equations an irrigation engineer would use. We hold out whole farms, never
> rows. And every model is scored against a naive baseline.
>
> That last one mattered. Our first salinity model scored R-squared 0.98 — and
> lost to 'assume nothing changes', because soil salinity moves slowly enough that
> the naive answer is very good. We reframed it to forecast the 30-day *change*,
> and now it beats that baseline by 29%. A metric without its baseline is
> marketing."

---

## Likely questions

**"Why not use real data?"**
> We evaluated three — USDA's ECe samples, the Songnen Plain raster, and the Kaggle
> farming sets. None pair salinity time series with weather at field scale: they're
> point samples, or satellite rasters, or EC as a fertility proxy with no salinity
> target. The CSV ingestion path is built and the feature schema doesn't change, so
> real data drops in the moment we have it.

**"How accurate is it really?"**
> Water stress, irrigation and health sit at R² 0.85, 0.74 and 0.85 against
> held-out farms. Salinity change is 0.28 — genuinely harder, because a month of
> future irrigation is partly unknowable. It beats the naive baseline by 29% on
> MAE, and I'd rather show you that number than a flattering one.

**"What if the internet drops during judging?"**
> It keeps working. Weather is cached in SQLite with a stale fallback, and the
> seeded history is local. You'd see a small "showing cached forecast" notice.

**"Does this need an API key?"**
> No. Open-Meteo is keyless, and it's also the better fit — it publishes FAO-56
> reference evapotranspiration directly, which is the strongest driver in the
> model. There's an OpenWeatherMap adapter behind the same interface.
