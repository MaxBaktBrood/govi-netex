import matplotlib.pyplot as plt
import typing
import geopandas

def plot_layer(layer: geopandas.GeoDataFrame, output_folder: str):
    # px = 1/plt.rcParams['figure.dpi']

    plt.rcParams["figure.dpi"] = 2000

    ax = layer.plot(
        # figsize=(1920*px, 1080*px)

    )

    ax.set_axis_off()
    ax.scatter(range(3000), range(3000), rasterized=True)

    plt.savefig(f'{output_folder}/netex.svg', transparent=True, format='svg')