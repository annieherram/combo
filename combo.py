import compat
from dependencies_manager import *

import argparse


def main():
    parser = argparse.ArgumentParser(description='Combo arguments.')
    # parser.add_argument('integers', metavar='N', type=int, nargs='+',
    #                     help='an integer for the accumulator')
    # parser.add_argument('--sum', dest='accumulate', action='store_const',
    #                     const=sum, default=max,
    #                     help='sum the integers (default: find the max)')
    parser.add_argument('path')

    args = parser.parse_args()
    # print (args.accumulate(args.integers))

    DependenciesManager(args.path).resolve()


if __name__ == '__main__':
    main()
