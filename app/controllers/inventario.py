from flask import Blueprint, render_template, request, redirect, url_for, flash
from models.producto import Producto
from models.categoria import Categoria

bp = Blueprint("inventario", __name__)


@bp.route("/")
def index():
    termino = request.args.get("q", "").strip()
    if termino:
        productos = Producto.buscar(termino)
    else:
        productos = Producto.get_all()
    stock_bajo = Producto.stock_bajo()
    return render_template(
        "productos/lista.html",
        productos=productos,
        stock_bajo=stock_bajo,
        termino=termino,
    )


@bp.route("/productos/nuevo", methods=["GET", "POST"])
def crear():
    categorias = Categoria.get_all()
    if request.method == "POST":
        nombre = request.form["nombre"].strip()
        descripcion = request.form.get("descripcion", "").strip()
        categoria_id = request.form.get("categoria_id") or None
        precio = request.form.get("precio", 0)
        stock = request.form.get("stock", 0)
        stock_minimo = request.form.get("stock_minimo", 5)

        if not nombre:
            flash("El nombre es obligatorio.", "danger")
            return render_template("productos/crear.html", categorias=categorias)

        Producto.create(nombre, descripcion, categoria_id, precio, stock, stock_minimo)
        flash(f'Producto "{nombre}" creado correctamente.', "success")
        return redirect(url_for("inventario.index"))

    return render_template("productos/crear.html", categorias=categorias)


@bp.route("/productos/<int:producto_id>")
def detalle(producto_id):
    producto = Producto.get_by_id(producto_id)
    if producto is None:
        flash("Producto no encontrado.", "warning")
        return redirect(url_for("inventario.index"))
    movimientos = Producto.get_movimientos(producto_id)
    return render_template(
        "productos/detalle.html", producto=producto, movimientos=movimientos
    )


@bp.route("/productos/<int:producto_id>/editar", methods=["GET", "POST"])
def editar(producto_id):
    producto = Producto.get_by_id(producto_id)
    if producto is None:
        flash("Producto no encontrado.", "warning")
        return redirect(url_for("inventario.index"))

    categorias = Categoria.get_all()
    if request.method == "POST":
        nombre = request.form["nombre"].strip()
        descripcion = request.form.get("descripcion", "").strip()
        categoria_id = request.form.get("categoria_id") or None
        precio = request.form.get("precio", 0)
        stock_minimo = request.form.get("stock_minimo", 5)

        if not nombre:
            flash("El nombre es obligatorio.", "danger")
            return render_template(
                "productos/editar.html", producto=producto, categorias=categorias
            )

        Producto.update(producto_id, nombre, descripcion, categoria_id, precio, stock_minimo)
        flash(f'Producto "{nombre}" actualizado.', "success")
        return redirect(url_for("inventario.detalle", producto_id=producto_id))

    return render_template(
        "productos/editar.html", producto=producto, categorias=categorias
    )


@bp.route("/productos/<int:producto_id>/eliminar", methods=["POST"])
def eliminar(producto_id):
    producto = Producto.get_by_id(producto_id)
    if producto:
        Producto.delete(producto_id)
        flash(f'Producto "{producto["nombre"]}" eliminado.', "info")
    return redirect(url_for("inventario.index"))


@bp.route("/productos/<int:producto_id>/movimiento", methods=["POST"])
def movimiento(producto_id):
    tipo = request.form["tipo"]
    cantidad = int(request.form.get("cantidad", 0))
    observacion = request.form.get("observacion", "").strip()

    if cantidad <= 0:
        flash("La cantidad debe ser mayor a 0.", "danger")
    else:
        Producto.registrar_movimiento(producto_id, tipo, cantidad, observacion)
        flash(f"Movimiento de {tipo} registrado: {cantidad} unidades.", "success")

    return redirect(url_for("inventario.detalle", producto_id=producto_id))
