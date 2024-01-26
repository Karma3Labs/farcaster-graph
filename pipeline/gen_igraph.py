# standard dependencies
from pathlib import Path
import argparse
import logging

# local dependencies
import utils
from config import Config
from timer import Timer

# 3rd party dependencies
import igraph as ig
import pandas as pd

def main(incsv:Path,  outpkl:Path, logger:logging.Logger):
  with Timer(name="read_csv"):
    edges_df = pd.read_csv(incsv)
  logger.info(utils.df_info_to_string(edges_df, with_sample=True))
  with Timer(name="df_to_igraph"):
    g = ig.Graph.DataFrame(edges_df, directed=True, use_vids=False)
  logger.info(ig.summary(g))
  with Timer(name="write_pickle"):
    g.write_pickle(outpkl)


if __name__ == '__main__':

  parser = argparse.ArgumentParser()
  parser.add_argument("-i", "--incsv",
                      help="input localtrust csv file",
                      required=True,
                      type=lambda f: Path(f).expanduser().resolve())  
  parser.add_argument("-o", "--outpkl",
                    help="output igraph pickle file",
                    required=True,
                    type=lambda f: Path(f).expanduser().resolve())
  args = parser.parse_args()
  print(args)
  print(Config.__dict__)

  logger = logging.getLogger()
  utils.setup_filelogger(logger, __file__)
  logger.setLevel(logging.DEBUG)
  utils.setup_consolelogger(logger)

  main(incsv=args.incsv, outpkl=args.outpkl, logger=logger)