import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import numpy as np

VARIANT_NUMBER = 60

root = tk.Tk()
root.title(f"Дашборд: Вариант {VARIANT_NUMBER}")
root.geometry("1000x700")
root.configure(bg="#f0f2f5")

df_raw = None # Исходные данные
df_work = None # Рабочая копия
fig = plt.Figure(figsize=(9, 5.5), dpi=100)
canvas = None
current_chart = "line"
station_var = None

# ________________________Настройка шрифтов для кириллицы__________________
plt.rcParams['font.sans-serif'] = ['Arial', 'DejaVu Sans', 'Liberation Sans']
plt.rcParams['axes.unicode_minus'] = False

df_raw = pd.read_csv(r'C:\Users\5830m\Dropbox\labs\proga\laba6\data.csv')
station_var = tk.StringVar(value="Все")

ctrl_frame = tk.Frame(root, bg="#f0f2f5")
ctrl_frame.pack(fill=tk.X, padx=10, pady=5)

#___________________4 этапа фильтрации__________________________
def preprocess_data():
    data = df_raw.copy()

    data = data[~np.isnan(data['uv'])]
    data = data[~np.isnan(data['ozone'])]
    data = data[~np.isnan(data['pm25'])]
    data = data[~np.isnan(data['aqi'])]

    str_anom = (
        (data['uv'] < 0) |
        (data['uv'] > 11) |
        (data['ozone'] < 0) |
        (data['pm25'] < 0) |
        (data['aqi'] < 0)
    )

    dol = str_anom.sum() / len(data) * 100

    #print(f"Количество аномальных строк: {str_anom.sum()}")
    #print(f"Доля аномальных строк: {dol:.2f}%")

    data['ozone'] = np.where(data['ozone'] < 0, 0, data['ozone'])
    data['pm25'] = np.where(data['pm25'] < 0, 0, data['pm25'])

    data['uv'] = np.clip(data['uv'], 0, 11)




    dell = 1e-8

    aqi = data['aqi'].astype(float)

    s_del = np.nan_to_num(data['ozone'], nan=1)
    s_del = np.where(s_del == 0, dell, s_del)

    smog = (data['pm25'] * data['aqi']) / s_del

    smog = np.nan_to_num(smog, nan=0, posinf=0, neginf=0)

    data['smog'] = smog.astype(np.float32)

    mean_a = np.nanmean(aqi)

    data['danger'] = ((data['uv'] > 7) & (aqi > mean_a)).astype(np.int8)

    total_replaced = 0
    group_replacements = {}

    groups = data['stat_id'].unique()

    for g in groups:

        mask = data['stat_id'] == g

        group_vals = data.loc[mask, 'pm25']

        q1 = np.percentile(group_vals, 25)
        q3 = np.percentile(group_vals, 75)

        iqr = q3 - q1

        low = q1 - 1.5 * iqr
        high = q3 + 1.5 * iqr

        median = np.median(group_vals)

        outliers = ((group_vals < low) | (group_vals > high))

        replaced_count = outliers.sum()

        data.loc[mask & outliers, 'pm25'] = median

        group_replacements[g] = replaced_count
        total_replaced += replaced_count

    share_replaced = total_replaced / len(data)

    #print("Заменено всего:", total_replaced)
    #print("Доля замен:", round(share_replaced, 4))


    mask_bad = ((data['uv'] < 0) | (data['uv'] > 11) | (data['ozone'] < 0) | (data['pm25'] < 0) | (data['aqi'] < 0) | (data['aqi'] > 500))

    bad_count = np.sum(mask_bad)
    bad_share = bad_count / len(data)

    #print("Количество нарушений:", bad_count)
    #print("Доля нарушений:", round(bad_share, 4))

    data['uv'] = np.clip(data['uv'], 0, 11)
    data['ozone'] = np.where(data['ozone'] < 0, 0, data['ozone'])
    data['pm25'] = np.where(data['pm25'] < 0, 0, data['pm25'])
    data['aqi'] = np.clip(data['aqi'], 0, 500)

    return data

#___________________ Контейнер для графика__________________________
plot_frame = tk.Frame(root, bg="white", relief=tk.SUNKEN, bd=1)
plot_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

# ____________________Адаптер matplotlib -> Tkinter__________________
canvas = FigureCanvasTkAgg(fig, master=plot_frame)
canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

#_________________ Панель инструментов (зум, сохранение, сброс вида)_____
toolbar = NavigationToolbar2Tk(canvas, plot_frame)
toolbar.update()
toolbar.pack(side=tk.TOP, fill=tk.X)

#___________________Очистка графиков__________________________
def clear_figure():
    fig.clear()

#фильтр по станции
def get_filtered_data():
    sel = station_var.get()
    if sel == "Все":
        return df_work.copy()
    return df_work.loc[df_work['stat_id'] == int(sel)].copy()

def on_station_change(event=None):
    change_chart(current_chart)

#___________________Plot - линейный__________________________
def plot_line():
    clear_figure()

    ax = fig.add_subplot(111)

    data = get_filtered_data()

    data['uv_round'] = data['uv'].round().astype(int)
    avg_pm25 = data.groupby('uv_round')['pm25'].mean()

    ax.plot(avg_pm25.index, avg_pm25.values, marker='o')

    ax.set_title("Средний pm25 по УФ-индексу")
    ax.set_xlabel("УФ-индекс")
    ax.set_ylabel("PM2.5")

    ax.grid(True)

    fig.tight_layout()
    canvas.draw_idle()

#___________________Bar - столбчатая диаграмма__________________________
def plot_bar():
    clear_figure()

    ax = fig.add_subplot(111)

    data = get_filtered_data()

    data['uv_round'] = data['uv'].round().astype(int)
    counts = data['uv_round'].value_counts().sort_index()

    ax.bar(counts.index.astype(str), counts.values)

    ax.set_title("Количество замеров по УФ-индексу")
    ax.set_xlabel("УФ-индекс")
    ax.set_ylabel("Количество")

    fig.tight_layout()
    canvas.draw_idle()

#___________________Scatter - диаграмма рассеяния__________________________
def plot_scatter():
    clear_figure()

    ax = fig.add_subplot(111)

    data = get_filtered_data()

    ax.scatter(data['pm25'], data['aqi'], alpha=0.6)

    ax.set_title("PM2.5 vs AQI")
    ax.set_xlabel("PM2.5")
    ax.set_ylabel("AQI")

    fig.tight_layout()
    canvas.draw_idle()

#___________________Heatmap - тепловая карта__________________________
def plot_heat_map():
    clear_figure()

    ax = fig.add_subplot(111)

    data = get_filtered_data()

    corr = data[['uv', 'ozone', 'pm25', 'aqi', 'smog']].corr()

    sns.heatmap(corr, annot=True, cmap='coolwarm', ax=ax)

    ax.set_title("Тепловая карта")

    fig.tight_layout()
    canvas.draw_idle()

#___________________Boxenplot - диграмма размаха(новая версия)__________________________
def kdel_plot():
    clear_figure()

    ax = fig.add_subplot(111)

    data = get_filtered_data()

    def aqi_spec(aqi):
        if pd.isna(aqi):
            return "0"
        elif aqi <= 50:
            return "good"
        elif aqi <= 100:
            return "moderate"
        else:
            return "unhealthy"
    
    data['aqi_spec'] = data['aqi'].apply(aqi_spec)

    sns.boxenplot(
        data=data,
        x="aqi_spec",
        y="aqi",
        order=['good', 'moderate', 'unhealthy'],
        ax=ax
    )

    ax.set_title("Пример 1")
    ax.set_xlabel("Категория качества воздуха")
    ax.set_ylabel("AQI")
    fig.tight_layout()
    canvas.draw_idle()

#___________________Boxplot - диграмма размаха(старая версия)__________________________
def att_his():
    clear_figure()

    ax = fig.add_subplot(111)

    data = get_filtered_data()

    def uv_spec(uv):
        if pd.isna(uv):
            return "0"
        elif uv < 3:
            return "low_uv"
        elif uv < 6:
            return "medium_uv"
        else:
            return "high_uv"

    data['uv_spec'] = data['uv'].apply(uv_spec)

    sns.boxplot(
        data=data,
        x="uv_spec",
        y="uv",
        order=['low_uv', 'medium_uv', 'high_uv'],
        ax=ax
    )

    ax.set_title("Пример 2")
    ax.set_xlabel("Тип УФ-индекса")
    ax.set_ylabel("UV")
    fig.tight_layout()
    canvas.draw_idle()

#___________________Выбор графиков__________________________
def change_chart(chart_type):
    global current_chart

    current_chart = chart_type

    if chart_type == "line":
        plot_line()

    elif chart_type == "bar":
        plot_bar()

    elif chart_type == "scatter":
        plot_scatter()

    elif chart_type == "heat":
        plot_heat_map()
    
    elif chart_type == "imp":
        kdel_plot()
    
    elif chart_type == "imp2":
        att_his()

#___________________Экспорт графиков__________________________
def export_plot():
    filepath = filedialog.asksaveasfilename(defaultextension=".png",
    filetypes=[("PNG", "*.png"), ("PDF", "*.pdf")])
    if filepath:
        fig.savefig(filepath, dpi=300, bbox_inches='tight')

tk.Label(ctrl_frame, text="Станция:", bg="#f0f2f5").pack(side=tk.LEFT, padx=4)
station_combo = ttk.Combobox(
    ctrl_frame,
    textvariable=station_var,
    values=["Все"] + sorted(df_raw['stat_id'].unique().astype(str).tolist(), key=int),
    width=10,
    state="readonly"
)
station_combo.pack(side=tk.LEFT, padx=4)
station_combo.bind("<<ComboboxSelected>>", on_station_change)

#_____________________Панель кнопок_____________________
tk.Button(
    ctrl_frame,
    text="Линейный",
    command=lambda: change_chart("line"),
    width=14
).pack(side=tk.LEFT, padx=4)

tk.Button(
    ctrl_frame,
    text="Столбчатый",
    command=lambda: change_chart("bar"),
    width=14
).pack(side=tk.LEFT, padx=4)

tk.Button(
    ctrl_frame,
    text="Scatter",
    command=lambda: change_chart("scatter"),
    width=14
).pack(side=tk.LEFT, padx=4)

tk.Button(
    ctrl_frame,
    text="HeatMap",
    command=lambda: change_chart("heat"),
    width=14
).pack(side=tk.LEFT, padx=4)

tk.Button(
    ctrl_frame,
    text="Boxenplot",
    command=lambda: change_chart("imp"),
    width=14
).pack(side=tk.LEFT, padx=4)

tk.Button(
    ctrl_frame,
    text="Boxplot",
    command=lambda: change_chart("imp2"),
    width=14
).pack(side=tk.LEFT, padx=4)


df_work = preprocess_data()
root.update()
plot_line()
root.mainloop()
