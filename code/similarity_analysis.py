'''
Code for comparing the algorithmic outputs in an MDS and hierarchical
clustering analysis.
'''

import pickle
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.transforms as transforms
from sklearn.manifold import MDS
from scipy.spatial import distance
from scipy.cluster import hierarchy
import eyekit
import core

plt.rcParams['svg.fonttype'] = 'none' # don't convert fonts to curves in SVGs
plt.rcParams.update({'font.size': 7})


class Dendrogram:

	def __init__(self, linkage_matrix, object_names, object_colors):
		self.linkage_matrix = linkage_matrix
		self.tree = hierarchy.to_tree(linkage_matrix)
		self.object_names = object_names
		self.object_colors = object_colors
		self.node_points = {}
		self._vertical_positions(self.tree)
		self._horizontal_positions()

	def _vertical_positions(self, node, level=0):
		self.node_points[node.get_id()] = [None, -level]
		if not node.is_leaf():
			self._vertical_positions(node.get_left(), level+1)
			self._vertical_positions(node.get_right(), level+1)

	def _horizontal_positions(self):
		_, axis = plt.subplots(1, 1)
		dg = hierarchy.dendrogram(self.linkage_matrix, ax=axis)
		leaf_X = axis.get_xticks()
		positions = dict(zip(dg['leaves'], leaf_X))
		for i, merger in enumerate(self.linkage_matrix, len(dg['leaves'])):
			positions[i] = np.mean([positions[int(merger[0])], positions[int(merger[1])]])
		for node_id in positions.keys():
			self.node_points[node_id][0] = positions[node_id]

	def _recursive_adjust(self, node, target, spacing, adjustment=0):
		node_id = node.get_id()
		L, R = node.get_left(), node.get_right()
		adjustment_l, adjustment_r = None, None
		if node_id == target:
			x = self.node_points[node_id][0]
			original_left_x = self.node_points[L.get_id()][0]
			original_right_x = self.node_points[R.get_id()][0]
			self.node_points[L.get_id()][0] = x - spacing / 2
			self.node_points[R.get_id()][0] = x + spacing / 2
			adjustment_l = self.node_points[L.get_id()][0] - original_left_x
			adjustment_r = self.node_points[R.get_id()][0] - original_right_x
		elif adjustment:
			self.node_points[L.get_id()][0] += adjustment
			self.node_points[R.get_id()][0] += adjustment
		if not L.is_leaf():
			if adjustment_l is not None:
				adjustment = adjustment_l
			self._recursive_adjust(L, target, spacing, adjustment)
		if not R.is_leaf():
			if adjustment_r is not None:
				adjustment = adjustment_r
			self._recursive_adjust(R, target, spacing, adjustment)

	def _recursive_plot(self, node, axis):
		node_id = node.get_id()
		if node.is_leaf():
			x, y = self.node_points[node_id]
			object_name = self.object_names[node_id]
			axis.scatter([x], [y], c=self.object_colors[object_name])
			axis.annotate(object_name, (x, y-0.2), va='top', ha='center', fontsize=7)
			return # Leaf node, break recursion
		L, R = node.get_left(), node.get_right()
		left_node_id, right_node_id = L.get_id(), R.get_id()
		X = [self.node_points[left_node_id][0], self.node_points[node_id][0], self.node_points[right_node_id][0]]
		Y = [self.node_points[left_node_id][1], self.node_points[node_id][1], self.node_points[right_node_id][1]]
		axis.plot(X, Y, c='black', zorder=0)
		self._recursive_plot(L, axis)
		self._recursive_plot(R, axis)

	def adjust_branch_spacing(self, node_spacing):
		'''
		Adjust the spacing at a set of branch points.
		'''
		for node_ids, spacing in node_spacing:
			adjustment = spacing / 2
			for node_id in node_ids:
				self._recursive_adjust(self.tree, node_id, adjustment)

	def plot(self, axis):
		'''
		Plot the dendrogram on a given axis.
		'''
		self._recursive_plot(self.tree, axis)
		branch_nodes = zip(*[xy for node_id, xy in self.node_points.items() if node_id >= len(self.object_names)])
		axis.scatter(*branch_nodes, c='black')
		min_x, max_x = axis.get_xlim()
		axis.set_xlim(min_x-2, max_x+2)
		min_y, max_y = axis.get_ylim()
		axis.set_ylim(min_y-0.25, 0.25)
		axis.set_xticks([])
		axis.set_yticks([])


def algorithmic_output_distance(method1, method2):
	from algorithms import dynamic_time_warping
	data1 = eyekit.io.read(core.FIXATIONS / f'{method1}.json')
	data2 = eyekit.io.read(core.FIXATIONS / f'{method2}.json')
	results = []
	for trial_id, trial in data1.items():
		fixation_XY1 = np.array([f.xy for f in trial['fixations'] if not f.discarded], dtype=int)
		fixation_XY2 = np.array([f.xy for f in data2[trial_id]['fixations'] if not f.discarded], dtype=int)
		cost, _ = dynamic_time_warping(fixation_XY1, fixation_XY2)
		results.append(cost)
	return np.median(results)

def make_algorithmic_distance_matrix(methods, filepath):
	distances = []
	for m1 in range(len(methods)):
		print(methods[m1])
		for m2 in range(m1+1, len(methods)):
			print('-', methods[m2])
			distances.append(algorithmic_output_distance(methods[m1], methods[m2]))
	matrix = distance.squareform(distances, 'tomatrix')
	with open(filepath, mode='wb') as file:
		pickle.dump((methods, matrix), file)

def min_max_normalize(positions):
	for i in range(positions.shape[1]):
		positions[:, i] = (positions[:, i] - positions[:, i].min()) / (positions[:, i].max() - positions[:, i].min())
	return positions

def subset_distance_matrix(algorithm_distances, subset_methods):
	original_methods, matrix = algorithm_distances
	new_matrix = np.zeros((len(subset_methods), len(subset_methods)), dtype=float)
	for i, method1 in enumerate(subset_methods):
		original_i = original_methods.index(method1)
		for j, method2 in enumerate(subset_methods):
			original_j = original_methods.index(method2)
			new_matrix[i, j] = matrix[original_i, original_j]
	return new_matrix

def hierarchical_clustering_analysis(algorithm_distances, methods):
	matrix = subset_distance_matrix(algorithm_distances, methods)
	condensed_matrix = distance.squareform(matrix, 'tovector')
	return methods, hierarchy.linkage(condensed_matrix, method='centroid')

def multidimensional_scaling_analysis(algorithm_distances, methods, random_seed=117):
	matrix = subset_distance_matrix(algorithm_distances, methods)
	mds = MDS(dissimilarity='precomputed', n_components=2, n_init=25, max_iter=2000, random_state=random_seed)
	positions = mds.fit_transform(matrix)
	return methods, min_max_normalize(positions)

def plot_analyses(ahc_solution, mds_solution, filepath):
	filepath = str(filepath)
	fig, axes = plt.subplots(2, 1, figsize=(3.3, 5))

	# Plot AHC clustering
	ahc_methods, linkage_matrix = ahc_solution
	method_names = {i:method for i, method in enumerate(ahc_methods)}
	dendrogram = Dendrogram(linkage_matrix, method_names, core.colors)
	dendrogram.adjust_branch_spacing([ ([9,10,11,12,13,15], 50),  ([14,16], 100) ])
	dendrogram.plot(axes[0])
	for node, label in [(9, 'Sequential'), (15, 'Positional'), (12, 'Relative'), (13, 'Absolute')]:
		x, y = dendrogram.node_points[node]
		axes[0].text(x+5, y, label, ha='left', va='center')
	inches_from_origin = (fig.dpi_scale_trans + transforms.ScaledTranslation(0, 1, axes[0].transAxes))
	axes[0].text(0.1, -0.1, 'a', fontsize=12, fontweight='bold', ha='left', va='top', transform=inches_from_origin)
	s, e = axes[0].get_xlim()
	padding = (e - s) * 0.05
	axes[0].set_xlim(s-padding, e+padding)
	s, e = axes[0].get_ylim()
	padding = (e - s) * 0.05
	axes[0].set_ylim(s-padding, e+padding)

	# Plot MDS solution
	mds_methods, positions = mds_solution
	mn, mx = positions[:, 0].min(), positions[:, 0].max()
	offset = (mx - mn) * 0.1
	furthest_method_to_right = mds_methods[np.argmax(positions[:, 0])]
	axes[1].scatter(positions[:, 0], positions[:, 1], color=[core.colors[m] for m in mds_methods])
	for label, position in zip(mds_methods, positions):
		if label == furthest_method_to_right or label == 'stretch':
			axes[1].text(position[0]-offset/3, position[1], label, va='center', ha='right')
		else:
			axes[1].text(position[0]+offset/3, position[1], label, va='center', ha='left')
	axes[1].set_xlim(mn-offset, mx+offset)
	mn, mx = positions[:, 1].min(), positions[:, 1].max()
	offset = (mx - mn) * 0.1
	axes[1].set_ylim(mn-offset, mx+offset)
	axes[1].set_xticks([])
	axes[1].set_yticks([])
	inches_from_origin = (fig.dpi_scale_trans + transforms.ScaledTranslation(0, 1, axes[1].transAxes))
	axes[1].text(0.1, -0.1, 'b', fontsize=12, fontweight='bold', ha='left', va='top', transform=inches_from_origin)

	fig.tight_layout(pad=0.5, h_pad=1, w_pad=1)
	fig.savefig(filepath, format='svg')
	core.format_svg_labels(filepath, monospace=core.algorithms, arbitrary_replacements={'gold':'Gold standard', 'JC':'Jon', 'VP':'Vale'})
	if not filepath.endswith('.svg'):
		core.convert_svg(filepath, filepath)


if __name__ == '__main__':

	# Measure pairwise distances between methods and pickle the distance matrix
	# make_algorithmic_distance_matrix(core.good_algorithms+['gold'], core.DATA / 'algorithm_distances.pkl')

	# Load the distance matrix created in the above step
	with open(core.DATA / 'algorithm_distances.pkl', mode='rb') as file:
		algorithm_distances = pickle.load(file)

	# Compute the hierarchical clustering solution
	ahc_solution = hierarchical_clustering_analysis(algorithm_distances, core.good_algorithms)

	# Compute the multidimensional scaling solution
	mds_solution = multidimensional_scaling_analysis(algorithm_distances, core.good_algorithms+['gold'], random_seed=9)

	# Plot the analyses
	# plot_analyses(ahc_solution, mds_solution, core.VISUALS / 'results_similarity.pdf')
	plot_analyses(ahc_solution, mds_solution, core.FIGS / 'fig12_single_column.eps')
