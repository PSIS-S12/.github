"""
PRIMAL2 Evaluation Script
=========================
Loads a trained model and evaluates it on a fixed, reproducible environment.
Measures throughput, success rate, episode length, collision rate, and more.

Usage:
    python evaluate.py --model_path model_astar3_continuous_0.5IL_ray2 \
                       --num_episodes 20 \
                       --num_agents 8 \
                       --max_steps 256 \
                       --save_gif

    # Compare two models:
    python evaluate.py --model_path model_baseline --compare_path model_heatmap \
                       --num_episodes 20
"""

import argparse
import numpy as np
import tensorflow as tf
import os
import sys
import copy
import json
import time
import random
import imageio
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

from Primal2Env import Primal2Env
from Primal2Observer import Primal2Observer
from Map_Generator import maze_generator
from Ray_ACNet import ACNet
from Env_Builder import make_gif
from parameters import (
    OBS_SIZE, NUM_FUTURE_STEPS, NUM_CHANNEL, DIAG_MVMT, a_size,
    GLOBAL_NET_SCOPE
)

# fixed map seed
EVAL_WORLD_SEED  = 42
EVAL_WORLD_SIZE  = 20
EVAL_WALL_COMP   = 5
EVAL_OBS_DENSITY = 0.3


def fixed_map_generator():
    """
    Generates one valid maze using the project's maze_generator with a fixed
    numpy seed, then freezes it. maze_generator returns (world, None) where
    world uses -1 for obstacles and 0 for free space.
    """
    np.random.seed(EVAL_WORLD_SEED)
    #random_state = np.random.get_state()

    gen = maze_generator(
        env_size=(EVAL_WORLD_SIZE, EVAL_WORLD_SIZE),
        wall_components=(EVAL_WALL_COMP, EVAL_WALL_COMP),
        obstacle_density=(EVAL_OBS_DENSITY, EVAL_OBS_DENSITY),
    )

    frozen_state, frozen_goals = gen()
    np.random.seed(None)

    print(f"  Fixed map shape: {frozen_state.shape}, "
          f"obstacles: {(frozen_state == -1).sum()}, "
          f"free cells: {(frozen_state == 0).sum()}")

    def _frozen_gen():
        return frozen_state.copy(), frozen_goals

    return _frozen_gen


def load_model(model_path, sess):
    """Load a trained model checkpoint into the session."""
    ckpt = tf.train.get_checkpoint_state(model_path)
    if ckpt is None:
        raise FileNotFoundError(f"No checkpoint found in: {model_path}")
    saver = tf.train.Saver()
    saver.restore(sess, ckpt.model_checkpoint_path)

    p = ckpt.model_checkpoint_path
    episode_num = 0
    try:
        import re
        numbers = re.findall(r'\d+', os.path.basename(p))
        if numbers:
            episode_num = int(numbers[-1])
    except Exception:
        episode_num = 0

    print(f"  Loaded checkpoint: {os.path.basename(p)} (episode ~{episode_num})")
    return episode_num

def run_episode(env, network, sess, num_agents, max_steps, save_gif=False,
                gif_path=None, strip_heatmap=False):
    """
    Run one episode on the fixed environment.

    Returns a dict of metrics:
        - targets_done    : total goals reached across all agents
        - throughput      : targets_done / max_steps  (goals per timestep)
        - episode_length  : number of steps taken
        - collisions      : number of collision events
        - timeout         : True if episode hit max_steps without finishing
        - success         : True if all agents reached their goal (one-shot)
        - step_rewards    : list of per-step total reward
    """
    env._reset()
    obs = env._observe()

    rnn_states = {i: network.state_init for i in range(1, num_agents + 1)}

    targets_done   = 0
    collisions     = 0
    step_rewards   = []
    gif_frames     = []

    if save_gif and gif_path:
        try:
            gif_frames.append(env._render())
        except Exception:
            save_gif = False

    for step in range(max_steps):
        actions = {}

        # Each agent picks an action independently
        for agent_id in range(1, num_agents + 1):
            s = obs[agent_id]
            # If baseline model (11 channels), strip the last heatmap channel
            obs_channels = s[0][:-1] if strip_heatmap else s[0]
            a_dist, v, rnn_out = sess.run(
                [network.policy, network.value, network.state_out],
                feed_dict={
                    network.inputs     : [obs_channels],
                    network.goal_pos   : [s[1]],
                    network.state_in[0]: rnn_states[agent_id][0],
                    network.state_in[1]: rnn_states[agent_id][1],
                }
            )
            rnn_states[agent_id] = rnn_out

            # Sample from policy distribution
            a_dist_flat = a_dist.flatten()
            action = np.random.choice(len(a_dist_flat), p=a_dist_flat)
            actions[agent_id] = action

        # Step environment
        all_obs, all_rewards = env.step_all(actions)

        step_reward = sum(all_rewards[i] for i in range(1, num_agents + 1))
        step_rewards.append(step_reward)

        # Count goals reached this step
        for agent_id in range(1, num_agents + 1):
            if env.world.agents[agent_id].status == 1:
                targets_done += 1

        # Count collisions
        collisions += sum(
            1 for i in range(1, num_agents + 1) if all_rewards[i] == -2
        )

        obs = all_obs

        if save_gif and gif_path:
            try:
                gif_frames.append(env._render())
            except Exception:
                save_gif = False

        # Check if all agents are done (one-shot mode)
        all_done = all(
            env.world.agents[i].status == 1 for i in range(1, num_agents + 1)
        )
        if all_done:
            break

    episode_length = step + 1
    timeout = episode_length >= max_steps and not all_done
    success = all_done

    if save_gif and gif_path and len(gif_frames) > 1:
        os.makedirs(os.path.dirname(gif_path) or '.', exist_ok=True)
        make_gif(np.array(gif_frames), gif_path)
        print(f"  GIF saved to: {gif_path}")

    return {
        'targets_done'  : targets_done,
        'throughput'    : targets_done / episode_length,
        'episode_length': episode_length,
        'collisions'    : collisions,
        'timeout'       : timeout,
        'success'       : success,
        'total_reward'  : sum(step_rewards),
        'step_rewards'  : step_rewards,
    }


def evaluate_model(model_path, num_episodes, num_agents, max_steps,
                   save_gif=False, gif_dir='eval_gifs', num_channels=None):
    """
    Evaluate a model over multiple episodes on the fixed environment.
    Returns aggregated metrics.
    """
    print(f"\n{'='*60}")
    print(f"  Evaluating: {model_path}")
    print(f"  Episodes: {num_episodes} | Agents: {num_agents} | Max steps: {max_steps}")
    effective_channels = num_channels if num_channels is not None else NUM_CHANNEL
    print(f"  Channels: {effective_channels} ({'heatmap' if effective_channels > 11 else 'baseline'})")
    print(f"{'='*60}")

    tf.reset_default_graph()
    config = tf.ConfigProto(allow_soft_placement=True, device_count={"GPU": 0})

    gen = fixed_map_generator()
    env = Primal2Env(
        num_agents=num_agents,
        observer=Primal2Observer(
            observation_size=OBS_SIZE,
            num_future_steps=NUM_FUTURE_STEPS
        ),
        map_generator=gen,
        IsDiagonal=DIAG_MVMT,
        isOneShot=False
    )
    strip_heatmap = (effective_channels == 11)

    original_reset = env._reset
    def fixed_reset(*args, **kwargs):
        np.random.seed(EVAL_WORLD_SEED)
        random.seed(EVAL_WORLD_SEED)
        result = original_reset(*args, **kwargs)
        np.random.seed(None)
        random.seed(None)
        return result
    env._reset = fixed_reset

    with tf.Session(config=config) as sess:
        network = ACNet(
            scope=GLOBAL_NET_SCOPE,
            a_size=a_size,
            trainer=None,
            TRAINING=False,
            NUM_CHANNEL=effective_channels,
            OBS_SIZE=OBS_SIZE,
            GLOBAL_NET_SCOPE=GLOBAL_NET_SCOPE,
            GLOBAL_NETWORK=False
        )

        sess.run(tf.global_variables_initializer())
        trained_episode = load_model(model_path, sess)

        all_metrics = []
        for ep in range(num_episodes):
            gif_path = None
            if save_gif and ep == 0:
                os.makedirs(gif_dir, exist_ok=True)
                model_name = os.path.basename(model_path)
                gif_path = os.path.join(gif_dir, f"{model_name}_ep{trained_episode}.gif")

            metrics = run_episode(
                env, network, sess, num_agents, max_steps,
                save_gif=(save_gif and ep == 0),
                gif_path=gif_path,
                strip_heatmap=strip_heatmap
            )
            all_metrics.append(metrics)

            print(f"  Episode {ep+1:3d}/{num_episodes} | "
                  f"targets={metrics['targets_done']:3d} | "
                  f"throughput={metrics['throughput']:.4f} | "
                  f"steps={metrics['episode_length']:3d} | "
                  f"success={'YES' if metrics['success'] else 'NO '} | "
                  f"collisions={metrics['collisions']:2d}")

    results = {
        'model_path'       : model_path,
        'trained_episode'  : trained_episode,
        'num_episodes'     : num_episodes,
        'num_agents'       : num_agents,
        'max_steps'        : max_steps,

        'throughput_mean'  : np.mean([m['throughput']    for m in all_metrics]),
        'throughput_std'   : np.std( [m['throughput']    for m in all_metrics]),
        'throughput_max'   : np.max( [m['throughput']    for m in all_metrics]),

        'targets_mean'     : np.mean([m['targets_done']  for m in all_metrics]),
        'targets_std'      : np.std( [m['targets_done']  for m in all_metrics]),

        'success_rate'     : np.mean([m['success']       for m in all_metrics]),
        'timeout_rate'     : np.mean([m['timeout']       for m in all_metrics]),

        'episode_len_mean' : np.mean([m['episode_length'] for m in all_metrics]),
        'episode_len_std'  : np.std( [m['episode_length'] for m in all_metrics]),

        'collision_mean'   : np.mean([m['collisions']    for m in all_metrics]),
        'collision_std'    : np.std( [m['collisions']    for m in all_metrics]),

        'reward_mean'      : np.mean([m['total_reward']  for m in all_metrics]),

        'raw'              : all_metrics,
    }

    print(f"\n Summary")
    print(f"  Throughput      : {results['throughput_mean']:.4f} ± {results['throughput_std']:.4f}")
    print(f"  Targets done    : {results['targets_mean']:.1f} ± {results['targets_std']:.1f}")
    print(f"  Success rate    : {results['success_rate']*100:.1f}%")
    print(f"  Timeout rate    : {results['timeout_rate']*100:.1f}%")
    print(f"  Episode length  : {results['episode_len_mean']:.1f} ± {results['episode_len_std']:.1f}")
    print(f"  Collisions      : {results['collision_mean']:.1f} ± {results['collision_std']:.1f}")
    print(f"  Avg reward      : {results['reward_mean']:.2f}")

    return results

def main():
    parser = argparse.ArgumentParser(description='Evaluate PRIMAL2 model(s)')
    parser.add_argument('--model_path',    type=str, required=True,
                        help='Path to trained model folder (required)')
    parser.add_argument('--compare_path',  type=str, default=None,
                        help='Optional second model path for comparison')
    parser.add_argument('--num_episodes',  type=int, default=20,
                        help='Number of evaluation episodes (default: 20)')
    parser.add_argument('--num_agents',    type=int, default=8,
                        help='Number of agents (default: 8, max: 8)')
    parser.add_argument('--max_steps',     type=int, default=256,
                        help='Max steps per episode (default: 256)')
    parser.add_argument('--save_gif',      action='store_true',
                        help='Save a GIF of the first episode')
    parser.add_argument('--gif_dir',       type=str, default='eval_gifs',
                        help='Directory to save GIFs (default: eval_gifs)')
    parser.add_argument('--output_dir',    type=str, default='eval_results',
                        help='Directory to save results and plots (default: eval_results)')
    parser.add_argument('--baseline',      action='store_true',
                        help='Load a baseline model (11 channels, no heatmap)')
    parser.add_argument('--compare_baseline', action='store_true',
                        help='Compare path is a baseline model (11 channels)')
    args = parser.parse_args()

    os.makedirs(args.output_dir, exist_ok=True)

    model_paths = [args.model_path]
    model_channels = [11 if args.baseline else NUM_CHANNEL]
    if args.compare_path:
        model_paths.append(args.compare_path)
        model_channels.append(11 if args.compare_baseline else NUM_CHANNEL)

    all_results = []
    for mp, ch in zip(model_paths, model_channels):
        results = evaluate_model(
            model_path   = mp,
            num_episodes = args.num_episodes,
            num_agents   = min(args.num_agents, 8),
            max_steps    = args.max_steps,
            save_gif     = args.save_gif,
            gif_dir      = args.gif_dir,
            num_channels = ch,
        )
        all_results.append(results)

        model_name = os.path.basename(mp)
        json_path  = os.path.join(args.output_dir, f'{model_name}_results.json')
        save_results = {k: v for k, v in results.items() if k != 'raw'}
        save_results['per_episode'] = [
            {k: v for k, v in m.items() if k != 'step_rewards'}
            for m in results['raw']
        ]
        with open(json_path, 'w') as f:
            json.dump(save_results, f, indent=2, default=float)
        print(f"  Results saved to: {json_path}")

    print(f"\nAll done. Results in: {args.output_dir}/")


if __name__ == '__main__':
    main()