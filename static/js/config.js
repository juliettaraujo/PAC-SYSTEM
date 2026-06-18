// Rellena el formulario de configuración para editar circuitos
function fillForm(id, name, nomen, volt, block, amps) {
    document.getElementById('form-title').innerText = 'Editar: ' + name;
    document.getElementById('circuit-form').action = '/update_circuit';
    document.getElementsByName('id')[0].value = id;
    document.getElementsByName('name')[0].value = name;
    document.getElementsByName('nomenclature')[0].value = nomen;
    document.getElementsByName('voltage')[0].value = volt;
    document.getElementsByName('block')[0].value = block;
    
    if(document.getElementsByName('amps')[0]) {
        document.getElementsByName('amps')[0].value = amps;
    }
}