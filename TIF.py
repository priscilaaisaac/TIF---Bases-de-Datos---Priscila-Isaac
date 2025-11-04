# -*- coding: utf-8 -*-
import psycopg2
import pandas as pd
import matplotlib.pyplot as plt
from tkinter import Tk, ttk, messagebox, Frame, Button, Toplevel, BOTH, END, LEFT, TOP, BOTTOM, W, X
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib import style
import sys
import datetime 
import numpy as np 

# ==============================================================================
# 🌟 CLASE PRINCIPAL DEL DASHBOARD 🌟
# ==============================================================================

class DashboardApp:
    # ⚠️ PALETA DE COLORES PERSONALIZADA
    COLORES_VIBRANTES = ["#B8E0D2", "#EA9087", "#CB8D9A", "#8497B5"] 
    
    # 📅 FECHAS ESTRATÉGICAS
    FECHA_SEIS_MESES_ATRAS = (datetime.date.today() - datetime.timedelta(days=6*30)).isoformat()
    
    # Estructura de consultas base: (SQL, Título, Eje X (col 0), Eje Y (col 1), Tipo de Visualización)
    # Tipos de Visualización: "barra", "torta", "lista", "multi_lista" (Nuevo para la consulta 13)
    CONSULTAS_BASE = [

    # 1. Ingresos Totales por Hotel en los últimos 6 meses
        (
            """
            SELECT h.nombre AS hotel, SUM(f.monto) AS ingresos_totales
            FROM factura f JOIN reserva r ON f.id_reserva = r.id_reserva
            JOIN reserva_incluye_habitacion ri ON r.id_reserva = ri.id_reserva
            JOIN habitacion hab ON ri.id_habitacion = hab.id_habitacion JOIN hotel h ON hab.id_hotel = h.id_hotel
            WHERE r.check_in >= '{fecha_seis_meses_atras}' 
            GROUP BY h.nombre ORDER BY ingresos_totales DESC;
            """,
            "Ingreso Total de cada Hotel en los últimos 6 meses", "Hotel", "Ingresos", "barra"
        ),
    # 2. Porcentaje aportado por cada hotel al ingrso global de la empresa
        (
            """
            SELECT h.nombre AS hotel, SUM(f.monto) AS ingresos_totales
            FROM factura f JOIN reserva r ON f.id_reserva = r.id_reserva
            JOIN reserva_incluye_habitacion ri ON r.id_reserva = ri.id_reserva
            JOIN habitacion hab ON ri.id_habitacion = hab.id_habitacion JOIN hotel h ON hab.id_hotel = h.id_hotel
            GROUP BY h.nombre ORDER BY ingresos_totales DESC;
            """,
            "Total de Ingresos aportado por Hotel (Histórico)", "Hotel", "Porcentaje de Ingresos", "torta"
        ),
    # 3. Empleados con Contrato Activo en 2023 o 2024
        (
            """
            SELECT 
                p.nombre, 
                p.apellido, 
                e.cargo,
                e.inicio_contrato,
                e.fin_contrato
            FROM empleado e
            JOIN persona p ON e.id_persona = p.id_persona 
            WHERE 
                (e.inicio_contrato <= '2024-12-31' AND (e.fin_contrato IS NULL OR e.fin_contrato >= '2023-01-01'))
            ORDER BY e.inicio_contrato ASC;
            """,
            "Empleados Activos o Contratados entre 2023 y 2024", "Nombre", "Fecha Ingreso", "lista"
        ),
    # 4. Sueldo Promedio por Cargo
        (
            """
            SELECT e.cargo, ROUND(AVG(e.sueldo), 2) AS sueldo_promedio
            FROM empleado e GROUP BY e.cargo ORDER BY sueldo_promedio DESC;
            """,
            "Sueldo Promedio por Cargo", "Cargo", "Sueldo Promedio", "barra"
        ),
    # 5. Empleados por Nivel de Ocupación (>10 vs <=10) <-- ¡NUEVO ELEMENTO CON TÍTULOS!
        (
            """
            -- Consulta 1: Empleados en hoteles con MÁS de 10 habitaciones ocupadas
            SELECT p.nombre, p.apellido, e.cargo, h.nombre AS hotel
            FROM persona p
            JOIN empleado e ON p.id_persona = e.id_persona
            JOIN hotel h ON h.id_hotel = e.id_hotel
            WHERE EXISTS (
                SELECT hab.id_hotel
                FROM habitacion hab
                WHERE hab.id_hotel = h.id_hotel AND hab.estado = 'ocupada'
                GROUP BY hab.id_hotel
                HAVING COUNT(hab.id_habitacion) > 10
            )
            ORDER BY h.nombre, p.apellido;
            
            ;;
            
            -- Consulta 2: Empleados en hoteles con MENOS o IGUAL de 10 habitaciones ocupadas
            SELECT p.nombre, p.apellido, e.cargo, h.nombre AS hotel
            FROM persona p
            JOIN empleado e ON p.id_persona = e.id_persona
            JOIN hotel h ON h.id_hotel = e.id_hotel
            WHERE NOT EXISTS (
                SELECT hab.id_hotel
                FROM habitacion hab
                WHERE hab.id_hotel = h.id_hotel AND hab.estado = 'ocupada'
                GROUP BY hab.id_hotel
                HAVING COUNT(hab.id_habitacion) > 10
            )
            ORDER BY h.nombre, p.apellido;
            """,
            "Empleados por Nivel de Ocupación (>10 vs <=10)", 
            "Nombre", 
            "Hotel", 
            ("multi_lista", ["Hoteles > 10 Ocupadas", "Hoteles <= 10 Ocupadas"]) # <-- ¡CAMBIO CLAVE!
        ),
    # 6. Método de Pago Más Elegido (Conteo)
        (
            """
            SELECT f.metodo_de_pago AS metodo_pago, COUNT(f.id_factura) AS cantidad_usos
            FROM factura f
            GROUP BY f.metodo_de_pago
            ORDER BY cantidad_usos DESC;
            """,
            "Método de Pago Más Elegido", "Método de Pago", "Cantidad de Usos", "torta"
        ),
    # 7. Total Facturado por Método de Pago
        (
            """
            SELECT f.metodo_de_pago AS metodo_pago, SUM(f.monto) AS total_facturado
            FROM factura f
            GROUP BY f.metodo_de_pago
            ORDER BY total_facturado DESC;
            """,
            "Total Facturado por Método de Pago", "Método de Pago", "Total Facturado", "barra"
        ),
    # 8. Huéspedes con Reservas Mayores a $100000 
        (
            """
            SELECT DISTINCT p.nombre, p.apellido, SUM(f.monto) AS total_reservado
            FROM huesped h
            JOIN persona p ON h.id_persona = p.id_persona 
            JOIN reserva r ON h.id_huesped = r.id_huesped
            JOIN factura f ON r.id_reserva = f.id_reserva
            GROUP BY p.id_persona, p.nombre, p.apellido
            HAVING SUM(f.monto) > 100000
            ORDER BY total_reservado DESC;
            """,
            "Huéspedes con Reservas Mayores a $100,000", "Nombre", "Total Facturado", "lista"
        ),
    # 10. Habitaciones en Mantenimiento en Todos los Hoteles
        (
            """
            SELECT h.nombre AS hotel, hab.id_habitacion, hab.estado
            FROM habitacion hab
            JOIN hotel h ON hab.id_hotel = h.id_hotel
            WHERE hab.estado = 'mantenimiento'
            ORDER BY h.nombre, hab.id_habitacion;
            """,
            "Habitaciones en Mantenimiento (Todos los Hoteles)", 
            "Hotel", 
            "ID Habitación", 
            "lista" 
        )
    ]
    
    DB_CONFIG = {
        'host': "localhost",
        'database': "TIF", 
        'user': "postgres",
        'password': "gloria",
        'options': '-c client_encoding=UTF8'
    }

    def __init__(self, master, custom_colors=None):
        self.master = master
        self.conn = None
        self.CONSULTAS = [] 
        self.canvas = None 
        
        if custom_colors:
             self.COLORES_VIBRANTES = custom_colors

        self.cargar_consultas() 
        
        # Iniciamos en la consulta de nacionalidades (índice 0)
        self.indice = 0
        self.tipo_grafico_actual = self.CONSULTAS[self.indice][4] 

        master.title("📊 Trabajo Integrador Final - Base de Datos - Priscila Isaac")
        master.geometry("1000x750")
        master.configure(bg="#fdf6f0") 
        master.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        self.main_frame = Frame(master, bg="#fdf6f0")
        self.main_frame.pack(side=TOP, fill=BOTH, expand=True)
        
        style.use('ggplot')
        
        self.fig = plt.Figure(figsize=(8, 6), facecolor="#fdf6f0")
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.main_frame)
        self.canvas_widget = self.canvas.get_tk_widget() 

        self.conectar_db()
        self.crear_controles()
        self.mostrar_grafico() 

# ------------------------------------------------------------------------------
    # ===== GESTIÓN DE CONSULTAS DINÁMICAS (Con Fecha) =====

    def cargar_consultas(self):
        """Calcula la fecha y construye la lista final de consultas, formateando el SQL."""
        
        self.CONSULTAS = []
        for query_base, title, x_label, y_label, chart_type in self.CONSULTAS_BASE:
            query_final = query_base.format(fecha_seis_meses_atras=self.FECHA_SEIS_MESES_ATRAS)
            self.CONSULTAS.append((query_final, title, x_label, y_label, chart_type))

# ------------------------------------------------------------------------------
    # ===== GESTIÓN DE LA BASE DE DATOS Y DATAFRAME (Funciones Centrales) =====

    def conectar_db(self):
        """Intenta conectar a la base de datos PostgreSQL."""
        try:
            self.conn = psycopg2.connect(**self.DB_CONFIG)
        except Exception as e:
            messagebox.showerror("Error de conexión", f"No se pudo conectar a PostgreSQL: {e}")
            self.conn = None 
            sys.exit(1)

    def on_closing(self):
        """Cierra la conexión a la DB y la ventana de Tkinter."""
        if self.conn:
            self.conn.close()
            print("Conexión a DB cerrada.")
        self.master.destroy()

    def obtener_dataframe(self, i, custom_query=None):
        """Ejecuta una consulta SQL y retorna un DataFrame de Pandas."""
        if not self.conn:
            return pd.DataFrame()

        query = custom_query if custom_query else self.CONSULTAS[i][0]
        
        # Manejar el caso de consultas múltiples (ej. Disponibilidad)
        if i == 13 and not custom_query:
            return self.ejecutar_consulta_disponibilidad(query)

        try:
            with self.conn.cursor() as cur:
                cur.execute("ROLLBACK;") 
                cur.execute(query)
                datos = cur.fetchall()
                columnas = [desc[0] for desc in cur.description]
                return pd.DataFrame(datos, columns=columnas)
        except Exception as e:
            messagebox.showerror("Error en consulta", f"No se pudo ejecutar la consulta: {e}")
            return pd.DataFrame()

# ------------------------------------------------------------------------------
    # ===== NUEVA FUNCIÓN PARA CONSULTA DE DISPONIBILIDAD (multi_lista) =====
    
    def ejecutar_consulta_disponibilidad(self, query):
        """
        Ejecuta las dos sub-consultas de disponibilidad/ocupación y 
        las muestra en un Toplevel con pestañas (Notebook).
        """
        if not self.conn:
            return None 

        consultas = query.split(';;')
        titulos = ["Habitaciones Disponibles", "Habitaciones Ocupadas"]
        
        # Abrir la ventana Toplevel para mostrar las pestañas
        top_disponibilidad = Toplevel(self.master)
        top_disponibilidad.title(self.CONSULTAS[self.indice][1])
        top_disponibilidad.geometry("550x400")
        top_disponibilidad.grab_set()

        notebook = ttk.Notebook(top_disponibilidad)
        notebook.pack(pady=10, padx=10, fill=BOTH, expand=True)

        dfs = []
        
        for idx, sub_query in enumerate(consultas):
            if not sub_query.strip():
                continue
            
            try:
                # 1. Obtener DataFrame
                with self.conn.cursor() as cur:
                    cur.execute("ROLLBACK;") 
                    cur.execute(sub_query)
                    datos = cur.fetchall()
                    columnas = [desc[0] for desc in cur.description]
                    df = pd.DataFrame(datos, columns=columnas)
                    dfs.append(df)
                    
                # 2. Crear Pestaña y Treeview
                frame_tab = Frame(notebook, bg="#fdf6f0")
                frame_tab.pack(fill=BOTH, expand=True)
                notebook.add(frame_tab, text=titulos[idx])
                
                self.mostrar_df_en_toplevel(frame_tab, df)

            except Exception as e:
                messagebox.showerror("Error de Sub-consulta", f"Error al ejecutar '{titulos[idx]}': {e}")
                
        # Retornamos el primer DF para evitar errores en mostrar_grafico, aunque la visualización se hizo aquí
        return dfs[0] if dfs else pd.DataFrame() 

    def mostrar_df_en_toplevel(self, frame_parent, df):
        """Helper para mostrar un DataFrame en un Treeview dentro de un Frame (usado en el Notebook)."""
        
        if df.empty:
            ttk.Label(frame_parent, text="No hay habitaciones en esta categoría.", font=("Arial", 10)).pack(pady=20)
            return

        v_scroll = ttk.Scrollbar(frame_parent, orient="vertical")
        v_scroll.pack(side="right", fill="y")
        h_scroll = ttk.Scrollbar(frame_parent, orient="horizontal")
        h_scroll.pack(side="bottom", fill="x")

        tree = ttk.Treeview(frame_parent, columns=list(df.columns), show="headings",
                             yscrollcommand=v_scroll.set, xscrollcommand=h_scroll.set)
        
        v_scroll.config(command=tree.yview)
        h_scroll.config(command=tree.xview)

        for col in df.columns:
            tree.heading(col, text=col.replace('_', ' ').title(), anchor=W)
            tree.column(col, width=150, anchor="center") 

        for _, row in df.iterrows():
            tree.insert("", END, values=list(row))
            
        tree.pack(fill=BOTH, expand=True, padx=5, pady=5)


# ------------------------------------------------------------------------------
    # ===== GESTIÓN DE GRÁFICOS Y DATOS (Limpieza y Dibujo) =====

    def mostrar_grafico(self):
        """Borra la visualización anterior y dibuja la nueva."""
        
        df = self.obtener_dataframe(self.indice)
        query_data = self.CONSULTAS[self.indice]
        _, titulo, eje_x, eje_y, tipo_sugerido = query_data

        if self.indice == 13 and tipo_sugerido == "multi_lista":
            # Si es la consulta especial, la lógica se ejecutó en obtener_dataframe/ejecutar_consulta_disponibilidad
            # Limpiamos el main_frame para mostrar el widget del gráfico (que podría estar cubierto)
            if self.canvas_widget.winfo_ismapped():
                self.canvas_widget.pack_forget()

            for widget in self.main_frame.winfo_children():
                if widget != self.canvas_widget:
                    widget.destroy()
            
            # Mostramos un mensaje de texto en el main_frame
            frame_msg = Frame(self.main_frame, bg="#fdf6f0")
            frame_msg.pack(pady=50)
            ttk.Label(frame_msg, text=titulo, font=("Arial", 16, "bold"), background="#fdf6f0", foreground="black").pack(pady=5)
            ttk.Label(frame_msg, text="Los resultados se muestran en una ventana emergente con pestañas.", font=("Arial", 12), background="#fdf6f0").pack()
            ttk.Label(frame_msg, text="Haga clic en 'Mostrar Tabla' para ver la información detallada.", font=("Arial", 12, "italic"), background="#fdf6f0").pack()
            return
            
        if df.empty:
            if not self.conn:
                return
            messagebox.showinfo("Sin datos", "No hay datos para mostrar en esta consulta.")
            return
        
        tipo_grafico_a_usar = self.tipo_grafico_actual if tipo_sugerido not in ["lista", "multi_lista"] else tipo_sugerido

        # ⚠️ Lógica para tipo "lista"
        if tipo_grafico_a_usar == "lista":
            if self.canvas_widget.winfo_ismapped():
                self.canvas_widget.pack_forget()

            for widget in self.main_frame.winfo_children():
                if widget != self.canvas_widget:
                    widget.destroy()
            
            self.mostrar_lista_treeview_main(df, titulo)
            return

        # --- LÓGICA PARA BARRAS Y TORTA ---
        
        # Limpiar Treeview o listas si están visibles
        for widget in self.main_frame.winfo_children():
            if widget != self.canvas_widget:
                widget.destroy()
                
        # Empaquetar el canvas
        if not self.canvas_widget.winfo_ismapped():
            self.canvas_widget.pack(side=TOP, fill=BOTH, expand=True) 
        
        self.fig.clear()
        ax = self.fig.add_subplot(111)
        columnas = df.columns
        
        # Ajustes de estilo (omito los detalles de estilo por brevedad, asumiendo que ya funcionan)

        if tipo_grafico_a_usar == "barra":
            
            es_metrica_dinero = any(term in titulo.lower() for term in ["ingresos", "sueldo", "facturado", "revpar", "adr", "total facturado"])
            
            if df[columnas[1]].dtype in ['int64', 'float64', 'object']: 
                
                def format_y_tick_dinero(value, pos):
                    return f'${int(value):,}' if value >= 1000 else f'${value:,.2f}'
                
                def format_y_tick_conteo(value, pos):
                    return f'{int(value):,}'
                
                # Manejar fechas en el Eje X 
                if df[columnas[0]].dtype == '<M8[ns]': 
                    df['mes_str'] = df[columnas[0]].dt.strftime('%b %Y')
                    ax.bar(df['mes_str'], df[columnas[1]], color=self.COLORES_VIBRANTES[:len(df)])
                    ax.set_xticklabels(df['mes_str'], rotation=45, ha="right", fontsize=8, color='black')
                    
                else:
                    ax.bar(df[columnas[0]], df[columnas[1]], color=self.COLORES_VIBRANTES[:len(df)])
                    ax.set_xticklabels(df[columnas[0]], rotation=0, ha="center", fontsize=8, color='black')

                if es_metrica_dinero:
                    ax.yaxis.set_major_formatter(plt.FuncFormatter(format_y_tick_dinero))
                else:
                    ax.yaxis.set_major_formatter(plt.FuncFormatter(format_y_tick_conteo))

            else:
                ax.bar(df[columnas[0]], df[columnas[1]], color=self.COLORES_VIBRANTES[:len(df)])
                ax.set_xticklabels(df[columnas[0]], rotation=0, ha="center", fontsize=8, color='black')

            ax.set_ylabel(eje_y, fontsize=10)
            ax.set_xlabel(eje_x, fontsize=10)
            
            
        elif tipo_grafico_a_usar == "torta":
             # Lógica del gráfico de torta (sin cambios)
             if columnas.size == 2 and ("porcentaje" in titulo.lower() or "elegido" in titulo.lower() or "ingresos" in titulo.lower()):
                try:
                    valores = df[columnas[1]].astype(float) 
                except ValueError:
                    messagebox.showwarning("Advertencia", "Los datos no son numéricos para un gráfico de torta. Mostrando barra.")
                    self.tipo_grafico_actual = "barra"
                    self.mostrar_grafico() 
                    return
                
                ax.pie(
                    valores, 
                    labels=df[columnas[0]], 
                    autopct="%1.1f%%",
                    startangle=90, 
                    colors=self.COLORES_VIBRANTES,
                    wedgeprops={'edgecolor': 'black', 'linewidth': 1}
                )
                ax.axis('equal') 
                self.tipo_grafico_actual = "torta"
             else:
                 messagebox.showwarning("Advertencia", f"La consulta '{titulo}' no es ideal para gráfico de torta. Mostrando barra.")
                 self.tipo_grafico_actual = "barra"
                 self.mostrar_grafico()
                 return 
        
        ax.set_title(titulo, fontsize=14, weight="bold", color="black")
        self.fig.tight_layout(pad=3.0)
        self.canvas.draw()
        
    def mostrar_lista_treeview_main(self, df, titulo):
        """Muestra la lista de datos en un formato de tabla Treeview en la ventana principal."""
        
        frame_lista = Frame(self.main_frame, bg="#fdf6f0")
        frame_lista.pack(pady=20, padx=50, fill=X)
        
        lbl_titulo = ttk.Label(frame_lista, text=titulo, font=("Arial", 14, "bold"), background="#fdf6f0", foreground="black")
        lbl_titulo.pack(pady=(0, 10))

        style = ttk.Style()
        style.configure("Custom.Treeview.Heading", font=('Arial', 10, 'bold'), background=self.COLORES_VIBRANTES[0], foreground="black")
        style.configure("Custom.Treeview", font=('Arial', 10), rowheight=25)

        columnas_tree = list(df.columns)
        
        # Scrollbars
        v_scroll = ttk.Scrollbar(frame_lista, orient="vertical")
        v_scroll.pack(side="right", fill="y")
        h_scroll = ttk.Scrollbar(frame_lista, orient="horizontal")
        h_scroll.pack(side="bottom", fill="x")
        
        tree = ttk.Treeview(frame_lista, columns=columnas_tree, show="headings", style="Custom.Treeview",
                            yscrollcommand=v_scroll.set, xscrollcommand=h_scroll.set)
        
        v_scroll.config(command=tree.yview)
        h_scroll.config(command=tree.xview)
        
        # Lógica de encabezados y anchos
        for col in columnas_tree:
             tree.heading(col, text=col.replace('_', ' ').title(), anchor=W)
             if "fecha" in col or "ingreso" in col:
                 tree.column(col, width=120, anchor=W)
             elif "total_reservado" in col:
                 tree.column(col, width=150, anchor="center")
             elif "apellido" in col or "nombre" in col:
                 tree.column(col, width=130, anchor=W)
             else:
                 tree.column(col, width=150, anchor=W)

        # Insertar datos
        for _, row in df.iterrows():
            formatted_row = []
            for val in row:
                if isinstance(val, (int)) and val >= 1000:
                    formatted_row.append(f'{val:,}')
                elif isinstance(val, (float)) and "total_reservado" in df.columns:
                    formatted_row.append(f'${val:,.2f}') # Formato moneda para reservas
                elif isinstance(val, (datetime.date, datetime.datetime)):
                    formatted_row.append(val.isoformat())
                else:
                    formatted_row.append(str(val))
            
            tree.insert("", END, values=formatted_row)
            
        tree.pack(fill=BOTH, expand=True)
        
    def mostrar_tabla(self):
        """
        Abre una ventana Toplevel para mostrar los datos en una tabla (Treeview) de la consulta actual.
        Si la consulta es de tipo 'multi_lista' (índice 13), llama a la función especial.
        """
        if self.CONSULTAS[self.indice][4] == "multi_lista":
            self.ejecutar_consulta_disponibilidad(self.CONSULTAS[self.indice][0])
            return
            
        df = self.obtener_dataframe(self.indice)
        if df.empty:
            messagebox.showinfo("Sin datos", "No hay datos para mostrar en la tabla.")
            return

        tabla = Toplevel(self.master)
        tabla.title(f"Datos: {self.CONSULTAS[self.indice][1]}")
        tabla.geometry("800x450")
        tabla.grab_set()

        frame_tabla = ttk.Frame(tabla, padding="10 10 10 10")
        frame_tabla.pack(fill=BOTH, expand=True)

        v_scroll = ttk.Scrollbar(frame_tabla, orient="vertical")
        v_scroll.pack(side="right", fill="y")
        h_scroll = ttk.Scrollbar(frame_tabla, orient="horizontal")
        h_scroll.pack(side="bottom", fill="x")

        tree = ttk.Treeview(frame_tabla, columns=list(df.columns), show="headings",
                             yscrollcommand=v_scroll.set, xscrollcommand=h_scroll.set)
        
        v_scroll.config(command=tree.yview)
        h_scroll.config(command=tree.xview)

        for col in df.columns:
            tree.heading(col, text=col.replace('_', ' ').title(), anchor=W)
            tree.column(col, width=150, anchor=W)

        for _, row in df.iterrows():
            formatted_row = []
            for val in row:
                if isinstance(val, (int)) and val >= 1000:
                    formatted_row.append(f'{val:,}')
                elif isinstance(val, (float)):
                    formatted_row.append(f'{val:,.2f}') 
                else:
                    formatted_row.append(str(val))
            
            tree.insert("", END, values=formatted_row)
            
        tree.pack(fill=BOTH, expand=True)


# ------------------------------------------------------------------------------
    # ===== NAVEGACIÓN Y CONTROLES (Sin cambios relevantes a la lógica) =====

    def siguiente(self):
        """Muestra el siguiente gráfico en la lista."""
        self.indice = (self.indice + 1) % len(self.CONSULTAS)
        self.tipo_grafico_actual = self.CONSULTAS[self.indice][4]
        self.mostrar_grafico()

    def anterior(self):
        """Muestra el gráfico anterior en la lista."""
        self.indice = (self.indice - 1) % len(self.CONSULTAS)
        self.tipo_grafico_actual = self.CONSULTAS[self.indice][4]
        self.mostrar_grafico()

    def cambiar_grafico(self):
        """Alterna entre gráfico de barra y torta si es una consulta apta."""
        if self.CONSULTAS[self.indice][4] in ["lista", "multi_lista"]:
            messagebox.showwarning("Cambio no permitido", "Esta es una lista/tabla y no puede cambiarse a gráfico.")
            return

        if self.obtener_dataframe(self.indice).shape[1] != 2:
            messagebox.showwarning("Cambio no permitido", "Esta consulta no es adecuada para un gráfico de torta.")
            return

        if self.tipo_grafico_actual == "barra":
            self.tipo_grafico_actual = "torta"
        elif self.tipo_grafico_actual == "torta":
            self.tipo_grafico_actual = "barra"
        
        self.mostrar_grafico()
        
    def crear_controles(self):
        """Crea el marco de botones en la parte inferior."""
        frame_botones = ttk.Frame(self.master, padding="10 10 10 10")
        frame_botones.pack(side=BOTTOM, pady=10)

        boton_color = self.COLORES_VIBRANTES[1] 
        boton_active_color = self.COLORES_VIBRANTES[2]
        
        style = ttk.Style()
        style.configure("TButton", font=("Segoe UI", 10, "bold"), padding=6, relief="raised",
                        background=boton_color, foreground="#222")
        style.map("TButton", 
                  background=[('active', boton_active_color)], 
                  foreground=[('active', 'white'), ('!active', 'black')])

        ttk.Button(frame_botones, text="⟵ Anterior", command=self.anterior).pack(side=LEFT, padx=10)
        ttk.Button(frame_botones, text="Cambiar Gráfico", command=self.cambiar_grafico).pack(side=LEFT, padx=10)
        ttk.Button(frame_botones, text="Mostrar Tabla", command=self.mostrar_tabla).pack(side=LEFT, padx=10)
        ttk.Button(frame_botones, text="Siguiente ⟶", command=self.siguiente).pack(side=LEFT, padx=10)


# ==============================================================================
# 🚀 EJECUCIÓN DEL CÓDIGO 🚀
# ==============================================================================

if __name__ == "__main__":
    # TUS COLORES DE REFERENCIA
    MIS_COLORES = ["#B8E0D2", "#EA9087", "#CB8D9A", "#8497B5"]
    
    ventana = Tk()
    app = DashboardApp(ventana, custom_colors=MIS_COLORES)
    ventana.mainloop()