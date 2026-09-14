import matplotlib.pyplot as plt
import pandas as pd



def plot_bar(
    df,
    x,
    y,
    path,
    title
):

    plt.figure(
        figsize=(8,5)
    )

    plt.bar(
        df[x],
        df[y]
    )

    plt.xticks(
        rotation=45,
        ha="right"
    )

    plt.title(
        title
    )

    plt.tight_layout()

    plt.savefig(
        path,
        dpi=300
    )

    plt.close()



def plot_heatmap(
    df,
    path
):

    matrix=df.set_index(
        "model"
    )

    plt.figure(
        figsize=(8,5)
    )

    plt.imshow(
        matrix.values,
        aspect="auto"
    )

    plt.xticks(
        range(len(matrix.columns)),
        matrix.columns,
        rotation=45,
        ha="right"
    )

    plt.yticks(
        range(len(matrix.index)),
        matrix.index
    )

    plt.colorbar()

    plt.tight_layout()

    plt.savefig(
        path,
        dpi=300
    )

    plt.close()
