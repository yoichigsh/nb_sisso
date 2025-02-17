#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys, datetime, threading, signal
import numpy as np
from scipy import integrate
from numba import njit, prange


def decryption(equation, columns=None):
    if columns is None:
        columns = [chr(i + 97) for i in range(np.max(equation))]
    stack = []
    if equation[0] == -100:
        return "0"
    for i in equation:
        match i:
            case 0:  # 1
                stack.append("1")
            case t if t > 0:  # number
                stack.append(columns[i - 1])
            case -1:  # +
                b, a = stack.pop(), stack.pop()
                stack.append(f"({a}+{b})")
            case -2:  # -
                b, a = stack.pop(), stack.pop()
                stack.append(f"({a}-{b})")
            case -3:  # *
                b, a = stack.pop(), stack.pop()
                stack.append(f"({a}*{b})")
            case -4:  # /
                b, a = stack.pop(), stack.pop()
                stack.append(f"({a}/{b})")
            case -5:  # *-1
                stack[len(stack) - 1] = f"({stack[len(stack)-1]}*-1)"
            case -6:  # ^-1
                stack[len(stack) - 1] = f"({stack[len(stack)-1]}**-1)"
            case -7:  # ^2
                stack[len(stack) - 1] = f"({stack[len(stack)-1]}**2)"
            case -8:  # sqrt
                stack[len(stack) - 1] = f"np.sqrt({stack[len(stack)-1]})"
            case -9:  # | |
                stack[len(stack) - 1] = f"np.abs({stack[len(stack)-1]})"
            case -10:  # ^3
                stack[len(stack) - 1] = f"({stack[len(stack)-1]}**3)"
            case -11:  # cbrt
                stack[len(stack) - 1] = f"np.cbrt({stack[len(stack)-1]})"
            case -12:  # ^6
                stack[len(stack) - 1] = f"({stack[len(stack)-1]}**6)"
            case -13:  # exp
                stack[len(stack) - 1] = f"np.exp({stack[len(stack)-1]})"
            case -14:  # exp-
                stack[len(stack) - 1] = f"np.exp(-1*{stack[len(stack)-1]})"
            case -15:  # log
                stack[len(stack) - 1] = f"np.log({stack[len(stack)-1]})"
            case -16:  # sin
                stack[len(stack) - 1] = f"np.sin({stack[len(stack)-1]})"
            case -17:  # cos
                stack[len(stack) - 1] = f"np.cos({stack[len(stack)-1]})"
            case -18:  # scd
                stack[len(stack) - 1] = f"np.scd({stack[len(stack)-1]})"
    return stack[0]


@njit(error_model="numpy", cache=True)  # parallel=True,
def eq_list_to_num(x, eq_list):
    return_arr = np.empty((eq_list.shape[0], x.shape[1]))
    for i in range(eq_list.shape[0]):
        return_arr[i] = calc_RPN(x, eq_list[i])
    return return_arr


## ------------------ Not use ------------------


def raise_and_log(logger, error):
    logger.error(error)  # exception()
    raise error


def type_check(logger, var, var_name, type_):
    if not isinstance(var, type_):
        raise_and_log(
            logger,
            TypeError(f"Expected variable '{var_name}' to be of type {type_}, but got {type(var)}."),
        )


def dtype_shape_check(logger, var, var_name, dtype_=None, ndim=None, dict_index_len=None):
    type_check(logger, var, var_name, np.ndarray)
    if not dtype_ is None:
        if var.dtype != dtype_:
            raise_and_log(
                logger,
                ValueError(f"Expected dtype for variable '{var_name}' to be {dtype_}, but got {var.dtype}."),
            )
    if not ndim is None:
        if var.ndim != ndim:
            raise_and_log(
                logger,
                ValueError(f"Expected ndim for variable '{var_name}' to be {ndim}, but got {var.ndim}."),
            )
    if not dict_index_len is None:
        for k, v in dict_index_len.items():
            if var.shape[k] != v:
                raise_and_log(
                    logger,
                    ValueError(
                        f"Expected size for dimension {k} of variable '{var_name}' to be {v}, but got {var.shape[k]}."
                    ),
                )


@njit(parallel=True)
def thread_check(num_threads):
    checker = np.zeros(num_threads, dtype="bool")
    for thread_id in prange(num_threads):
        checker[thread_id] = True
    return np.all(checker)


@njit(error_model="numpy")
def argmin_and_min(arr):
    min_num1, min_num2, min_index = arr[0, 0], arr[0, 1], 0
    for i in range(1, arr.shape[0]):
        if min_num1 > arr[i, 0]:
            min_num1, min_num2, min_index = arr[i, 0], arr[i, 1], i
        elif min_num1 == arr[i, 0]:
            if min_num2 > arr[i, 1]:
                min_num1, min_num2, min_index = arr[i, 0], arr[i, 1], i
    return min_num1, min_num2, min_index


@njit(error_model="numpy")  # ,fastmath=True)
def calc_RPN(x, equation):
    # Nan_number=-100
    stack = np.full((np.sum(equation >= 0), x.shape[1]), np.nan, dtype="float64")
    last_stack_index = -1
    for i in range(equation.shape[0]):
        last_op = equation[i]
        if last_op == 0:
            last_stack_index += 1
            stack[last_stack_index] = 1
        if last_op > 0:
            last_stack_index += 1
            stack[last_stack_index] = x[last_op - 1]
        else:
            match last_op:
                case -1:  # +
                    last_stack_index -= 1
                    stack[last_stack_index] += stack[last_stack_index + 1]
                case -2:  # -
                    last_stack_index -= 1
                    stack[last_stack_index] -= stack[last_stack_index + 1]
                case -3:  # *
                    last_stack_index -= 1
                    stack[last_stack_index] *= stack[last_stack_index + 1]
                case -4:  # /
                    last_stack_index -= 1
                    stack[last_stack_index] /= stack[last_stack_index + 1]
                case -5:  # *-1
                    stack[last_stack_index] *= -1
                case -6:  # ^-1
                    stack[last_stack_index] **= -1
                case -7:  # ^2
                    stack[last_stack_index] **= 2
                case -8:  # sqrt
                    # only x>=0
                    if np.any(stack[last_stack_index] < 0):
                        stack[0, 0] = np.nan
                        return stack[0]
                    stack[last_stack_index] **= 0.5
                case -9:  # | |
                    # not all(x>=0),all(x<0)
                    if (0 >= np.max(stack[last_stack_index])) or (np.min(stack[last_stack_index]) >= 0):
                        stack[0, 0] = np.nan
                        return stack[0]
                    stack[last_stack_index] = np.abs(stack[last_stack_index])
                case -10:  # ^3
                    stack[last_stack_index] **= 3
                case -11:  # cbrt
                    # only x>=0
                    if np.any(stack[last_stack_index] < 0):
                        stack[0, 0] = np.nan
                        return stack[0]
                    stack[last_stack_index] = np.cbrt(stack[last_stack_index])
                case -12:  # ^6
                    stack[last_stack_index] **= 6
                case -13:  # exp
                    stack[last_stack_index] = np.exp(stack[last_stack_index])
                case -14:  # exp-
                    stack[last_stack_index] = np.exp(-stack[last_stack_index])
                case -15:  # log
                    # only x>=0
                    if np.any(stack[last_stack_index] < 0):
                        stack[0, 0] = np.nan
                        return stack[0]
                    stack[last_stack_index] = np.log(stack[last_stack_index])
                case -16:  # sin
                    stack[last_stack_index] = np.sin(stack[last_stack_index])
                case -17:  # cos
                    stack[last_stack_index] = np.cos(stack[last_stack_index])
                case -18:  # scd
                    stack[last_stack_index] = np.sin(stack[last_stack_index])  # よくわからないため未実装
                case -100:  # END
                    break  # None
    if np.any(np.isinf(stack[last_stack_index])):  # 演算子の意味があるか
        stack[0, 0] = np.nan
    elif np.any(np.isnan(stack[last_stack_index])):
        stack[0, 0] = np.nan
    elif is_zero(stack[last_stack_index]):
        stack[0, 0] = np.nan
    elif is_one(stack[last_stack_index]):
        stack[0, 0] = np.nan
    # if is_const(stack[0]):
    # stack[0,0]=np.nan
    return stack[0]


@njit(error_model="numpy")  # ,fastmath=True)
def is_zero(num):
    rtol = 1e-010
    return np.all(np.abs(num) <= rtol)


@njit(error_model="numpy")  # ,fastmath=True)
def is_one(num):
    rtol = 1e-010
    if (np.abs(num[0]) - 1) <= rtol:
        if is_const(num):
            return True
    return False


@njit(error_model="numpy")  # ,fastmath=True)
def is_const(num):
    rtol = 1e-010
    return (np.max(num) - np.min(num)) / np.abs(np.mean(num)) <= rtol


@njit(error_model="numpy")  # ,fastmath=True)
def jit_cov(X, ddof=1):
    n = X.shape[1]
    X_1 = X[0, :] - np.sum(X[0, :]) / n
    X_2 = X[1, :] - np.sum(X[1, :]) / n
    var_1 = np.sum(X_1 * X_1) / (n - ddof)  # 不偏分散、sklearnに準拠
    var_2 = np.sum(X_2 * X_2) / (n - ddof)
    cross_cov = np.sum(X_1 * X_2) / (n - ddof)
    return var_1, var_2, cross_cov


@njit(error_model="numpy")  # ,fastmath=True)
def quartile_deviation(x):
    n_samples = x.shape[0]
    n_4 = n_samples // 4
    sorted_x = np.sort(x)
    match n_samples % 4:
        case 0:
            return (sorted_x[3 * n_4 - 1] + sorted_x[3 * n_4] - sorted_x[n_4 - 1] - sorted_x[n_4]) / 4
        case 1:
            return (sorted_x[3 * n_4] + sorted_x[3 * n_4 + 1] - sorted_x[n_4 - 1] - sorted_x[n_4]) / 4
        case 2:
            return (sorted_x[3 * n_4 + 1] - sorted_x[n_4]) / 2
        case 3:
            return (sorted_x[3 * n_4 + 2] - sorted_x[n_4]) / 2


def p_upper_x(n, x, pattern):
    def bin(x):
        # 二項分布の正規近似
        omega = n / pattern * (1 - 1 / pattern)
        return np.exp(-((x - n / 1 / pattern) ** 2) / (2 * omega)) / ((2 * np.pi * omega) ** 0.5)

    p, err = integrate.quad(bin, 0, x)
    return 1 - p**pattern


def sig_handler(signum, frame):
    sys.exit(1)


def emergency_save(logger, emergency_save_folder_path, **kwargs):
    now = datetime.datetime.now()
    file_path = f"{emergency_save_folder_path}/emergency_save_{now.strftime('%Y%m%d_%H%M%S')}"
    logger.error(f"emergency save path: {file_path}.npz")
    logger.error(f"emergency save keys: {list(kwargs.keys())}")
    np.savez(file_path, **kwargs)
