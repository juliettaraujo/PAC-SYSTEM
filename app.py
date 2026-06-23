from flask import Flask, render_template, request, redirect, flash, url_for
from flask import send_file
from openpyxl import Workbook
import os
import backend


app = Flask(__name__)
app.secret_key = 'pac_system_corpoelec'
backend.init_db()

# Esta función inyecta la lista de bloques automáticamente en el proyecto
@app.context_processor
def inject_blocks():
# Para cambiar, agregar o quitar bloques, se modifica aquí:
    bloques_operativos = ["A", "B", "C", "D"]
    return dict(BLOQUES=bloques_operativos)

@app.route('/')
def index():
    # 1. Obtenemos los circuitos separados por estado
    activos, consignados, _ = backend.get_all_circuits()
    
    # 2. LLAMAMOS a la función de estadísticas 
    total_dia, pac_mw, recuperados_mw = backend.get_mw_stats()
    
    # 3. Enviamos todas las variables al HTML
    return render_template('index.html', 
                circuits=activos, 
                consignados=consignados, 
                total_dia=total_dia, 
                pac_mw=pac_mw, 
                recuperados_mw=recuperados_mw)

@app.route('/config')
def config():
    _, _, all_c = backend.get_all_circuits()
    return render_template('config.html', circuits=all_c)

@app.route('/add_circuit', methods=['POST'])
def add_circuit():
    backend.add_circuit(
        request.form['name'], 
        request.form['nomenclature'], 
        request.form['voltage'], 
        request.form['block']
        ) 
    return redirect('/config')

@app.route('/update_circuit', methods=['POST'])
def update_circuit():
    backend.update_circuit(request.form['id'], request.form['name'], 
    request.form['nomenclature'], request.form['voltage'], 
    request.form['block'], request.form['amps'])
    return redirect('/config')

@app.route('/delete_circuit/<int:c_id>')
def delete_circuit(c_id):
    backend.delete_circuit(c_id)
    return redirect('/config')

@app.route('/update_monitor', methods=['POST'])
def update_monitor():
    backend.update_monitor(request.form['id'], request.form['status'], 
    request.form['start_time'], request.form['end_time'], 
    request.form['amps'])
    return redirect('/')

@app.route('/consign', methods=['GET', 'POST'])
def consign():

    if request.method == 'POST':

        name = request.form.get('name')
        nomenclature = request.form.get('nomenclature')
        action = request.form.get('action')

        if name and nomenclature and action:

            result = backend.toggle_consignation(
                name,
                nomenclature,
                action
            )

            if result:

                if action == 'consignar':
                    flash(f'Circuito {name} consignado correctamente', 'success')

                elif action == 'liberar':
                    flash(f'Circuito {name} liberado correctamente', 'success')

            else:
                flash('No se encontró el circuito', 'error')

            return redirect('/') # Siempre vuelve al inicio

@app.route('/history')
def history():
    # Cambiamos get_history() por la nueva función agrupada
    grouped_logs = backend.get_grouped_history()
    return render_template('history.html', grouped_logs=grouped_logs)

@app.route('/delete_history/<int:h_id>')
def delete_history(h_id):
    backend.delete_history_item(h_id)
    return redirect('/history')

@app.route('/export_history_excel')
def export_history_excel():

    conn = backend.get_db()

    rows = conn.execute('''
        SELECT *
        FROM history
        ORDER BY timestamp DESC
    ''').fetchall()

    conn.close()

    wb = Workbook()
    ws = wb.active

    ws.title = "Historial"

    headers = [
        "Fecha",
        "Circuito",
        "Nomenclatura",
        "Evento",
        "Detalles",
        "MW Afectados",
        "Hora Inicio",
        "Hora Fin",
        "Duración"
    ]

    ws.append(headers)

    for row in rows:

        ws.append([
            row["timestamp"],
            row["name"],
            row["nomenclature"],
            row["event"],
            row["details"],
            row["mw"],
            row["start_time"],
            row["end_time"],
            row["duration"]
        ])

    file_name = "Historial_CORPOELEC.xlsx"

    wb.save(file_name)

    return send_file(
        file_name,
        as_attachment=True
    )

@app.route('/reset_system', methods=['POST'])
def reset_system():
    backend.reset_system_states()
    flash('Sistema restablecido con éxito.', 'success')
    return redirect('/')


@app.route('/shift_change', methods=['POST'])
def shift_change():
    # Ejecutamos el cambio de guardia
    backend.perform_shift_change()
    # Recargamos de forma segura la pantalla principal del monitor
    return redirect('/')

@app.route('/clear_history')
def clear_history():
    # Conexión directa para ejecutar el vaciado completo del registro histórico
    conn = backend.get_db()
    conn.execute('DELETE FROM history')
    conn.commit()
    conn.close()
    flash('Historial de maniobras eliminado permanentemente.', 'success')
    return redirect('/history')

if __name__ == '__main__':
    app.run(debug=True)

    