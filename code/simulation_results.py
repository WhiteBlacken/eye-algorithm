'''
Code for plotting the simulation results.
'''

import pickle
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.transforms as transforms
from matplotlib import gridspec
import core

plt.rcParams['svg.fonttype'] = 'none' # don't convert fonts to curves in SVGs
plt.rcParams.update({'font.size': 7})


def plot_results(filepath, layout, n_rows=2, figsize=None, stagger=0):
	filepath = str(filepath)
	n_cols = len(layout) // n_rows
	if len(layout) % n_rows:
		n_cols += 1
	if figsize is None:
		figsize = (n_cols*4, n_rows*4)
	legend_patches = []
	fig, axes = plt.subplots(n_rows, n_cols, figsize=figsize, squeeze=False)
	subplot_i = 0
	for factor, (r, c) in zip(layout, np.ndindex((n_rows, n_cols))):
		if factor == 'legend':
			axes[r][c].axis('off')
			legend = axes[r][c].legend(legend_patches, core.algorithms, loc='center', frameon=False)
			for line in legend.get_lines():
				line.set_linewidth(2.5)
			continue
		with open(core.SIMULATIONS / f'{factor}.pkl', mode='rb') as file:
			results = pickle.load(file)
		results *= 100
		factor_label, (factor_min_val, factor_max_val) = core.factors[factor]
		factor_space = np.linspace(factor_min_val, factor_max_val, len(results[0]))
		for method_i, method in enumerate(core.algorithms):
			means = results[method_i, :].mean(axis=1)
			staggering = (method_i - (len(core.algorithms)-1) / 2) * stagger
			staggered_means = means - staggering
			line, = axes[r][c].plot(factor_space, staggered_means, color=core.colors[method], label=method, linewidth=1)
			if r == 0 and c == 0:
				legend_patches.append(line)
			axes[r][c].set_ylim(-5, 105)
			offset = (factor_max_val - factor_min_val) * 0.05
			axes[r][c].set_xlim(factor_min_val-offset, factor_max_val+offset)
			axes[r][c].set_xlabel(factor_label)
		inches_from_origin = (fig.dpi_scale_trans + transforms.ScaledTranslation(0, 0, axes[r][c].transAxes))
		axes[r][c].text(0.05, 0.05, '%s'%('abcde'[subplot_i]), fontsize=12, fontweight='bold', ha='left', va='bottom', transform=inches_from_origin)
		subplot_i += 1
	for axis in axes[:, 0]:
		axis.set_ylabel('Accuracy of algorithmic correction (%)')
	for axis in axes[:, 1:].flatten():
		axis.set_yticklabels([])
	for r, c in list(np.ndindex((n_rows, n_cols)))[len(layout):]:
		axes[r][c].axis('off')
	fig.tight_layout(pad=0.5, h_pad=1, w_pad=1)
	fig.savefig(filepath, format='svg')
	core.format_svg_labels(filepath, core.algorithms)
	if not filepath.endswith('.svg'):
		core.convert_svg(filepath, filepath)


def plot_invariance(filepath, show_percentages=False):
	filepath = str(filepath)
	accuracy = np.zeros((len(core.algorithms), len(core.factors)), dtype=float)
	invariance = np.zeros((len(core.algorithms), len(core.factors)), dtype=bool)
	for f, factor in enumerate(core.factors):
		with open(core.SIMULATIONS / f'{factor}.pkl', mode='rb') as file:
			results = pickle.load(file)
		for a, algorithm in enumerate(core.algorithms):
			accuracy[a, f] = results[a].mean() * 100
			if np.all(results[a] == 1.0):
				invariance[a, f] = True
	fig = plt.figure(figsize=(3.3, 2))
	gs = gridspec.GridSpec(1, 2, width_ratios=[20, 1])
	heatmap, legend = plt.subplot(gs[0]), plt.subplot(gs[1])
	im = heatmap.pcolor(accuracy, vmin=50, vmax=100, cmap='Greys')
	plt.colorbar(im, cax=legend)
	for (a, f), invariant in np.ndenumerate(invariance):
		if invariant:
			heatmap.text(f+0.5, a+0.5, '✔', color='white', ha='center', va='center', fontsize=12)
		elif show_percentages:
			heatmap.text(f+0.5, a+0.5, str(round(accuracy[a, f], 2)), color='white', ha='center', va='center')
	heatmap.invert_yaxis()
	heatmap.set_xticks(np.arange(5)+0.5)
	heatmap.set_xticklabels(['Noise', 'Slope', 'Shift', 'Within', 'Between'])
	heatmap.set_yticks(np.arange(len(core.algorithms))+0.5)
	heatmap.set_yticklabels(core.algorithms)
	heatmap.tick_params(bottom=False, left=False)
	legend.set_ylabel('Mean accuracy (%)', labelpad=-38)
	fig.tight_layout(pad=0.5, h_pad=1, w_pad=1)
	fig.savefig(filepath, format='svg')
	core.format_svg_labels(filepath, core.algorithms)
	if not filepath.endswith('.svg'):
		core.convert_svg(filepath, filepath)


if __name__ == '__main__':

	# plot_results(core.VISUALS / 'results_simulations.pdf', ['noise', 'slope', 'shift', 'regression_within', 'regression_between', 'legend'], 2, (7, 5), 0.75)
	plot_results(core.FIGS / 'fig04_double_column.eps', ['noise', 'legend', 'slope', 'shift', 'regression_within', 'regression_between'], 3, (6.8, 6), 0.75)
	
	# plot_invariance(core.VISUALS / 'results_invariance.pdf')
	plot_invariance(core.FIGS / 'fig05_single_column.eps')
