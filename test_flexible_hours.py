#!/usr/bin/env python
"""Test script for flexible working hours functions"""

import frappe
from datetime import datetime, time
from hrms.hr.doctype.shift_type.shift_type import round_time_to_precision, calculate_lunch_overlap_hours

def test_round_time_to_precision():
    print("=" * 60)
    print("Testing round_time_to_precision function")
    print("=" * 60)

    # Test check-in rounding (up) with 15 min precision
    test_cases_in = [
        (datetime(2025, 12, 22, 9, 0, 0), 15, 'up', "9:00 -> 9:00"),
        (datetime(2025, 12, 22, 9, 1, 0), 15, 'up', "9:01 -> 9:15"),
        (datetime(2025, 12, 22, 9, 12, 0), 15, 'up', "9:12 -> 9:15"),
        (datetime(2025, 12, 22, 9, 15, 0), 15, 'up', "9:15 -> 9:15"),
        (datetime(2025, 12, 22, 9, 16, 0), 15, 'up', "9:16 -> 9:30"),
        (datetime(2025, 12, 22, 9, 31, 0), 15, 'up', "9:31 -> 9:45"),
    ]

    print("\nCheck-in rounding (15 min precision):")
    for dt, precision, direction, desc in test_cases_in:
        result = round_time_to_precision(dt, precision, direction)
        print(f"  {desc}: {result.strftime('%H:%M')}")

    # Test check-out rounding (down) with 15 min precision
    test_cases_out = [
        (datetime(2025, 12, 22, 18, 0, 0), 15, 'down', "18:00 -> 18:00"),
        (datetime(2025, 12, 22, 17, 59, 0), 15, 'down', "17:59 -> 17:45"),
        (datetime(2025, 12, 22, 17, 47, 0), 15, 'down', "17:47 -> 17:45"),
        (datetime(2025, 12, 22, 17, 45, 0), 15, 'down', "17:45 -> 17:45"),
        (datetime(2025, 12, 22, 17, 44, 0), 15, 'down', "17:44 -> 17:30"),
        (datetime(2025, 12, 22, 17, 29, 0), 15, 'down', "17:29 -> 17:15"),
    ]

    print("\nCheck-out rounding (15 min precision):")
    for dt, precision, direction, desc in test_cases_out:
        result = round_time_to_precision(dt, precision, direction)
        print(f"  {desc}: {result.strftime('%H:%M')}")


def test_calculate_lunch_overlap_hours():
    print("\n" + "=" * 60)
    print("Testing calculate_lunch_overlap_hours function")
    print("=" * 60)

    lunch_start = time(12, 0)
    lunch_end = time(13, 0)

    test_cases_lunch = [
        (datetime(2025, 12, 22, 9, 0), datetime(2025, 12, 22, 18, 0), "9:00-18:00 -> 1.0h"),
        (datetime(2025, 12, 22, 9, 0), datetime(2025, 12, 22, 12, 0), "9:00-12:00 -> 0.0h"),
        (datetime(2025, 12, 22, 13, 0), datetime(2025, 12, 22, 18, 0), "13:00-18:00 -> 0.0h"),
        (datetime(2025, 12, 22, 11, 30), datetime(2025, 12, 22, 12, 30), "11:30-12:30 -> 0.5h"),
        (datetime(2025, 12, 22, 11, 30), datetime(2025, 12, 22, 14, 0), "11:30-14:00 -> 1.0h"),
        (datetime(2025, 12, 22, 12, 30), datetime(2025, 12, 22, 13, 30), "12:30-13:30 -> 0.5h"),
    ]

    print("\nLunch overlap (12:00-13:00):")
    for in_time, out_time, desc in test_cases_lunch:
        overlap = calculate_lunch_overlap_hours(in_time, out_time, lunch_start, lunch_end)
        print(f"  {desc}: {overlap}h")


def test_full_scenario():
    print("\n" + "=" * 60)
    print("Testing full scenario")
    print("=" * 60)

    lunch_start = time(12, 0)
    lunch_end = time(13, 0)

    # Full scenario test
    in_time = datetime(2025, 12, 22, 9, 12)
    out_time = datetime(2025, 12, 22, 17, 47)

    rounded_in = round_time_to_precision(in_time, 15, 'up')
    rounded_out = round_time_to_precision(out_time, 15, 'down')

    raw_hours = (rounded_out - rounded_in).total_seconds() / 3600
    lunch_overlap = calculate_lunch_overlap_hours(rounded_in, rounded_out, lunch_start, lunch_end)
    final_hours = raw_hours - lunch_overlap

    print(f"\nOriginal: {in_time.strftime('%H:%M')} - {out_time.strftime('%H:%M')}")
    print(f"Rounded:  {rounded_in.strftime('%H:%M')} - {rounded_out.strftime('%H:%M')}")
    print(f"Raw hours: {raw_hours}h")
    print(f"Lunch overlap: {lunch_overlap}h")
    print(f"Final hours: {final_hours}h")


def run_all_tests():
    test_round_time_to_precision()
    test_calculate_lunch_overlap_hours()
    test_full_scenario()
    print("\n" + "=" * 60)
    print("All tests completed!")
    print("=" * 60)


if __name__ == "__main__":
    run_all_tests()

