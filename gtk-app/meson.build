project('kindle-series-manager-gtk', 'cpp', version: 'v1.0.0', default_options: ['cpp_std=c++17'], meson_version: '>=1.1')

gtk_dep = dependency('gtk+-2.0')

sources = files(
    './src/main.cpp'
)

include_dirs = include_directories(
  './src/include/'
)

executable('kindle-series-manager-gtk', sources, include_directories: include_dirs, dependencies: [gtk_dep], cpp_args: '-static-libstdc++', link_args: '-static-libstdc++')
