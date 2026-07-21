let numeroActual = 0;

function abrirModal(numero){

    numeroActual = numero;

    document.getElementById(
        "numeroSeleccionado"
    ).innerText =
    numero.toString().padStart(3,"0");

    document.getElementById(
        "modalCompra"
    ).style.display = "flex";
}

function cerrarModal(){

    document.getElementById(
        "modalCompra"
    ).style.display = "none";
}

async function reservarNumero(){

    const nombre =
    document.getElementById(
        "nombre"
    ).value;

    const telefono =
    document.getElementById(
        "telefono"
    ).value;

    if(!nombre || !telefono){

        alert(
            "Completa todos los campos"
        );

        return;
    }

    const respuesta =
    await fetch("/reservar",{

        method:"POST",

        headers:{
            "Content-Type":
            "application/json"
        },

        body:JSON.stringify({

            numero:numeroActual,
            nombre:nombre,
            telefono:telefono

        })

    });

    const data =
    await respuesta.json();

    if(data.success){

        alert(
            "Número reservado correctamente"
        );

        location.reload();

    }else{

        alert(
            "Ese número ya está reservado"
        );

    }
}