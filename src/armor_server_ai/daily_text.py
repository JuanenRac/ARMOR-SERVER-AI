"""The readable text of the daily summary, from templates in the eight languages (Portuguese of Portugal); no service is called and nothing is generated.

Copyright (C) 2026 JuanenRac (Electro Hobby 3D). GPL-3.0-or-later.
"""

from __future__ import annotations

from typing import Any

TEXTS: dict[str, dict[str, str]] = {
    "en": {
        "title": "Daily summary", "empty": "No events were recorded.",
        "totals": "Events: {events}; alarms: {alarms} (serious: {serious}, false: {false_alarms}).", "busiest": "Busiest hour: {hour}:00 (events: {count}).",
        "serious_none": "No serious alarms.", "serious": "Serious alarms ({count}): {items}.",
        "links": "Nodes that lost their link: {items}.", "link_item": "{node} (x{count}, {seconds} s)",
        "outliers": "Outlying readings ({count}): {items}.", "outlier_item": "{node}/{sensor} = {value} at {time} (median {median})",
        "consumption": "Consumption: {samples} samples, mean {mean} W, maximum {max} W. Peaks: {items}.", "peak_item": "{watts} W at {time}",
        "patterns": "Patterns found:", "patterns_none": "No patterns found.", "evidence": "evidence",
        "hourly_repeat": "The alarm {code} in {zone} repeats at the same time of the hour ({count} hours: {hours}, within {tolerance} minutes).",
        "intermittent_sensor": "The sensor of {zone} on node {node} fails on and off ({count} faults, longest pause {gap} s).",
        "intermittent_link": "Node {node} keeps losing its link (losses: {count}).", "recurrent_false_alarm": "Recurring false alarms in {zone}: {count}.",
        "anomalous_consumption": "Consumption far above its moving average (times: {count}; more than {sigma} deviations and {ratio} times the mean of the last {window} samples).",
        "ai_note": "AI note",
    },
    "es": {
        "title": "Resumen diario", "empty": "No se registró ningún evento.",
        "totals": "Eventos: {events}; alarmas: {alarms} (graves: {serious}, falsas: {false_alarms}).", "busiest": "Hora con más actividad: {hour}:00 (eventos: {count}).",
        "serious_none": "Ninguna alarma grave.", "serious": "Alarmas graves ({count}): {items}.",
        "links": "Nodos que perdieron el enlace: {items}.", "link_item": "{node} (x{count}, {seconds} s)",
        "outliers": "Lecturas apartadas ({count}): {items}.", "outlier_item": "{node}/{sensor} = {value} a las {time} (mediana {median})",
        "consumption": "Consumo: {samples} muestras, media {mean} W, máximo {max} W. Picos: {items}.", "peak_item": "{watts} W a las {time}",
        "patterns": "Patrones encontrados:", "patterns_none": "No se encontró ningún patrón.", "evidence": "evidencia",
        "hourly_repeat": "La alarma {code} en {zone} se repite en el mismo momento de la hora ({count} horas: {hours}, con {tolerance} minutos de margen).",
        "intermittent_sensor": "El sensor de {zone} en el nodo {node} falla de forma intermitente ({count} fallos, la pausa más larga {gap} s).",
        "intermittent_link": "El nodo {node} pierde el enlace una y otra vez (pérdidas: {count}).", "recurrent_false_alarm": "Falsas alarmas recurrentes en {zone}: {count}.",
        "anomalous_consumption": "Consumo muy por encima de su media móvil (veces: {count}; más de {sigma} desviaciones y {ratio} veces la media de las últimas {window} muestras).",
        "ai_note": "Nota de la IA",
    },
    "de": {
        "title": "Tagesübersicht", "empty": "Es wurden keine Ereignisse aufgezeichnet.",
        "totals": "Ereignisse: {events}; Alarme: {alarms} (schwere: {serious}, Fehlalarme: {false_alarms}).", "busiest": "Aktivste Stunde: {hour}:00 Uhr (Ereignisse: {count}).",
        "serious_none": "Keine schweren Alarme.", "serious": "Schwere Alarme ({count}): {items}.",
        "links": "Knoten, die die Verbindung verloren haben: {items}.", "link_item": "{node} (x{count}, {seconds} s)",
        "outliers": "Ausreißer bei den Messwerten ({count}): {items}.", "outlier_item": "{node}/{sensor} = {value} um {time} (Median {median})",
        "consumption": "Verbrauch: {samples} Messwerte, Mittel {mean} W, Maximum {max} W. Spitzen: {items}.", "peak_item": "{watts} W um {time}",
        "patterns": "Gefundene Muster:", "patterns_none": "Keine Muster gefunden.", "evidence": "Belege",
        "hourly_repeat": "Der Alarm {code} in {zone} wiederholt sich zur gleichen Zeit der Stunde ({count} Stunden: {hours}, innerhalb von {tolerance} Minuten).",
        "intermittent_sensor": "Der Sensor von {zone} am Knoten {node} fällt immer wieder aus ({count} Ausfälle, längste Pause {gap} s).",
        "intermittent_link": "Der Knoten {node} verliert immer wieder die Verbindung (Verluste: {count}).", "recurrent_false_alarm": "Wiederkehrende Fehlalarme in {zone}: {count}.",
        "anomalous_consumption": "Der Verbrauch lag weit über seinem gleitenden Mittel (Mal: {count}; mehr als {sigma} Abweichungen und das {ratio}-Fache des Mittels der letzten {window} Messwerte).",
        "ai_note": "Hinweis der KI",
    },
    "fr": {
        "title": "Résumé quotidien", "empty": "Aucun événement n'a été enregistré.",
        "totals": "Événements : {events} ; alarmes : {alarms} (graves : {serious}, fausses : {false_alarms}).", "busiest": "Heure la plus chargée : {hour}h00 (événements : {count}).",
        "serious_none": "Aucune alarme grave.", "serious": "Alarmes graves ({count}) : {items}.",
        "links": "Nœuds ayant perdu leur liaison : {items}.", "link_item": "{node} (x{count}, {seconds} s)",
        "outliers": "Mesures aberrantes ({count}) : {items}.", "outlier_item": "{node}/{sensor} = {value} à {time} (médiane {median})",
        "consumption": "Consommation : {samples} échantillons, moyenne {mean} W, maximum {max} W. Pics : {items}.", "peak_item": "{watts} W à {time}",
        "patterns": "Motifs trouvés :", "patterns_none": "Aucun motif trouvé.", "evidence": "preuves",
        "hourly_repeat": "L'alarme {code} dans {zone} se répète au même moment de l'heure ({count} heures : {hours}, à {tolerance} minutes près).",
        "intermittent_sensor": "Le capteur de {zone} sur le nœud {node} tombe en panne par intermittence ({count} pannes, pause la plus longue {gap} s).",
        "intermittent_link": "Le nœud {node} perd sa liaison à répétition (pertes : {count}).", "recurrent_false_alarm": "Fausses alarmes récurrentes dans {zone} : {count}.",
        "anomalous_consumption": "Consommation très au-dessus de sa moyenne mobile (fois : {count} ; plus de {sigma} écarts et {ratio} fois la moyenne des {window} derniers échantillons).",
        "ai_note": "Note de l'IA",
    },
    "it": {
        "title": "Riepilogo giornaliero", "empty": "Nessun evento registrato.",
        "totals": "Eventi: {events}; allarmi: {alarms} (gravi: {serious}, falsi: {false_alarms}).", "busiest": "Ora più attiva: {hour}:00 (eventi: {count}).",
        "serious_none": "Nessun allarme grave.", "serious": "Allarmi gravi ({count}): {items}.",
        "links": "Nodi che hanno perso il collegamento: {items}.", "link_item": "{node} (x{count}, {seconds} s)",
        "outliers": "Letture anomale ({count}): {items}.", "outlier_item": "{node}/{sensor} = {value} alle {time} (mediana {median})",
        "consumption": "Consumo: {samples} campioni, media {mean} W, massimo {max} W. Picchi: {items}.", "peak_item": "{watts} W alle {time}",
        "patterns": "Schemi trovati:", "patterns_none": "Nessuno schema trovato.", "evidence": "prove",
        "hourly_repeat": "L'allarme {code} in {zone} si ripete nello stesso momento dell'ora ({count} ore: {hours}, entro {tolerance} minuti).",
        "intermittent_sensor": "Il sensore di {zone} sul nodo {node} si guasta a intermittenza ({count} guasti, pausa più lunga {gap} s).",
        "intermittent_link": "Il nodo {node} perde il collegamento ripetutamente (perdite: {count}).", "recurrent_false_alarm": "Falsi allarmi ricorrenti in {zone}: {count}.",
        "anomalous_consumption": "Consumo molto sopra la sua media mobile (volte: {count}; oltre {sigma} deviazioni e {ratio} volte la media degli ultimi {window} campioni).",
        "ai_note": "Nota dell'IA",
    },
    "ja": {
        "title": "日次サマリー", "empty": "イベントは記録されませんでした。",
        "totals": "イベント {events} 件、アラーム {alarms} 件（重大 {serious} 件、誤報 {false_alarms} 件）。", "busiest": "最も多かった時間帯：{hour}:00（{count} 件）。",
        "serious_none": "重大なアラームはありません。", "serious": "重大なアラーム（{count} 件）：{items}。",
        "links": "通信が途切れたノード：{items}。", "link_item": "{node}（x{count}、{seconds} 秒）",
        "outliers": "外れた測定値（{count} 件）：{items}。", "outlier_item": "{node}/{sensor} = {value}（{time}、中央値 {median}）",
        "consumption": "消費電力：{samples} サンプル、平均 {mean} W、最大 {max} W。ピーク：{items}。", "peak_item": "{watts} W（{time}）",
        "patterns": "見つかったパターン：", "patterns_none": "パターンは見つかりませんでした。", "evidence": "根拠",
        "hourly_repeat": "{zone} のアラーム {code} が毎時ほぼ同じ時刻に繰り返されています（{count} 時間帯：{hours}、許容 {tolerance} 分）。",
        "intermittent_sensor": "ノード {node} の {zone} のセンサーが断続的に故障しています（{count} 回、最長の間隔 {gap} 秒）。",
        "intermittent_link": "ノード {node} は通信が {count} 回途切れました。", "recurrent_false_alarm": "{zone} で誤報が {count} 件。",
        "anomalous_consumption": "消費電力が移動平均を大きく上回った回数：{count}（標準偏差の {sigma} 倍超、かつ直近 {window} サンプルの平均の {ratio} 倍以上）。",
        "ai_note": "AI のメモ",
    },
    "zh": {
        "title": "每日摘要", "empty": "没有记录到任何事件。",
        "totals": "{events} 个事件，{alarms} 次报警（严重 {serious} 次，误报 {false_alarms} 次）。", "busiest": "最繁忙的时段：{hour}:00，共 {count} 个事件。",
        "serious_none": "没有严重报警。", "serious": "严重报警（{count} 次）：{items}。",
        "links": "失去连接的节点：{items}。", "link_item": "{node}（x{count}，{seconds} 秒）",
        "outliers": "偏离的读数（{count} 个）：{items}。", "outlier_item": "{node}/{sensor} = {value}（{time}，中位数 {median}）",
        "consumption": "用电量：{samples} 个样本，平均 {mean} W，最大 {max} W。峰值：{items}。", "peak_item": "{watts} W（{time}）",
        "patterns": "发现的规律：", "patterns_none": "没有发现规律。", "evidence": "依据",
        "hourly_repeat": "{zone} 的报警 {code} 在每小时的同一时刻重复出现（{count} 个小时：{hours}，误差 {tolerance} 分钟内）。",
        "intermittent_sensor": "节点 {node} 上 {zone} 的传感器时好时坏（{count} 次故障，最长间隔 {gap} 秒）。",
        "intermittent_link": "节点 {node} 的连接中断了 {count} 次。", "recurrent_false_alarm": "{zone} 出现 {count} 次误报。",
        "anomalous_consumption": "用电量有 {count} 次远高于其移动平均值（超过 {sigma} 个标准差，且达到最近 {window} 个样本平均值的 {ratio} 倍）。",
        "ai_note": "AI 备注",
    },
    "pt": {
        "title": "Resumo diário", "empty": "Não foi registado nenhum evento.",
        "totals": "Eventos: {events}; alarmes: {alarms} (graves: {serious}, falsos: {false_alarms}).", "busiest": "Hora com mais atividade: {hour}:00 (eventos: {count}).",
        "serious_none": "Nenhum alarme grave.", "serious": "Alarmes graves ({count}): {items}.",
        "links": "Nós que perderam a ligação: {items}.", "link_item": "{node} (x{count}, {seconds} s)",
        "outliers": "Leituras afastadas ({count}): {items}.", "outlier_item": "{node}/{sensor} = {value} às {time} (mediana {median})",
        "consumption": "Consumo: {samples} amostras, média {mean} W, máximo {max} W. Picos: {items}.", "peak_item": "{watts} W às {time}",
        "patterns": "Padrões encontrados:", "patterns_none": "Não foi encontrado nenhum padrão.", "evidence": "evidências",
        "hourly_repeat": "O alarme {code} em {zone} repete-se no mesmo momento da hora ({count} horas: {hours}, com {tolerance} minutos de margem).",
        "intermittent_sensor": "O sensor de {zone} no nó {node} avaria de forma intermitente ({count} avarias, a pausa mais longa {gap} s).",
        "intermittent_link": "O nó {node} perde a ligação repetidamente (perdas: {count}).", "recurrent_false_alarm": "Falsos alarmes recorrentes em {zone}: {count}.",
        "anomalous_consumption": "Consumo muito acima da sua média móvel (vezes: {count}; mais de {sigma} desvios e {ratio} vezes a média das últimas {window} amostras).",
        "ai_note": "Nota da IA",
    },
}


def clock(t_s: float) -> str:
    seconds = int(t_s)
    return f"{seconds // 3600:02d}:{seconds % 3600 // 60:02d}:{seconds % 60:02d}"


def _subject(finding: dict[str, Any]) -> dict[str, Any]:
    return {"code": "", "zone": "-", "node": "", **finding["subject"]}


def _finding_line(texts: dict[str, str], finding: dict[str, Any]) -> str:
    detail, kind = finding["detail"], finding["kind"]
    values: dict[str, Any] = {**_subject(finding), "count": finding["count"]}
    if kind == "hourly_repeat":
        values |= {"hours": ", ".join(f"{h}:00" for h in detail["hours"]), "tolerance": detail["tolerance_min"]}
    elif kind == "intermittent_sensor":
        values |= {"gap": detail["max_gap_s"]}
    elif kind == "anomalous_consumption":
        values |= {"window": detail["window"], "sigma": detail["sigma"], "ratio": detail["min_ratio"]}
    evidence = ", ".join(clock(item["t_s"]) for item in finding["evidence"])
    return f"- {texts[kind].format(**values)} ({texts['evidence']}: {evidence})"


def render_text(summary: dict[str, Any], findings: list[dict[str, Any]], language: str = "en") -> str:
    """The summary and the findings as text in the language (English when it is not one of the eight)."""
    texts = TEXTS.get(language, TEXTS["en"])
    lines = [texts["title"]]
    totals = summary["totals"]
    if not totals["events"]:
        return "\n".join([*lines, texts["empty"]])
    lines.append(texts["totals"].format(events=totals["events"], alarms=totals["alarms"], serious=totals["serious_alarms"], false_alarms=totals["false_alarms"]))
    lines.append(texts["busiest"].format(hour=summary["busiest_hour"], count=summary["by_hour"][summary["busiest_hour"]]))
    if summary["serious_alarms"]:
        items = ", ".join(f"{a['code']} {a.get('zone', '-')} {clock(a['t_s'])}" for a in summary["serious_alarms"])
        lines.append(texts["serious"].format(count=len(summary["serious_alarms"]), items=items))
    else:
        lines.append(texts["serious_none"])
    if summary["nodes_link_lost"]:
        lines.append(texts["links"].format(items=", ".join(texts["link_item"].format(node=n["node"], count=n["count"], seconds=n["total_s"]) for n in summary["nodes_link_lost"])))
    if summary["outlier_readings"]:
        items = ", ".join(texts["outlier_item"].format(node=o["node"], sensor=o["sensor"], value=o["value"], time=clock(o["t_s"]), median=o["median"]) for o in summary["outlier_readings"])
        lines.append(texts["outliers"].format(count=len(summary["outlier_readings"]), items=items))
    consumption = summary["consumption"]
    if consumption["samples"]:
        peaks = ", ".join(texts["peak_item"].format(watts=p["watts"], time=clock(p["t_s"])) for p in consumption["peaks"])
        lines.append(texts["consumption"].format(samples=consumption["samples"], mean=consumption["mean_w"], max=consumption["max_w"], items=peaks))
    lines.append(texts["patterns"] if findings else texts["patterns_none"])
    lines.extend(_finding_line(texts, finding) for finding in findings)
    return "\n".join(lines)
