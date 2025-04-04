# Coverage Summary and To-Do List

## Current Status (as of April 3, 2025)

| Module | Coverage | Status |
|--------|----------|--------|
| repomap/__init__.py | 100% | ✅ Complete |
| repomap/__main__.py | 100% | ✅ Complete |
| repomap/dump.py | 100% | ✅ Complete |
| repomap/io_utils.py | 100% | ✅ Complete |
| repomap/special.py | 100% | ✅ Complete |
| repomap/models.py | 83% | ✅ Good enough |
| repomap/utils.py | 18% | 🔄 In Progress |
| repomap/install_queries.py | 0% | 🔄 In Progress |
| repomap/api.py | 0% | ❌ Not started |
| repomap/repomap.py | 6% | 🔄 In Progress |
| repomap/section_splitting.py | 4% | 🔄 In Progress |
| **TOTAL** | **12%** | 🚫 Far from target |

## Test Files Created/Updated

1. `tests/test_special.py` - Tests for the special.py module (100% coverage)
2. `tests/test_dump.py` - Tests for the dump.py module (100% coverage)
3. `tests/test_models_comprehensive.py` - Comprehensive tests for the models.py module (83% coverage)
4. `tests/test_io_utils_comprehensive.py` - Comprehensive tests for the io_utils.py module (100% coverage)
5. `tests/test_main_module.py` - Tests for the __main__.py module (100% coverage)

## To-Do List (To Reach 80% Coverage)

Based on the number of missing lines, here are the priorities:

### High Priority

1. `repomap/repomap.py` (1166 missing lines)
   - Create tests for the core functionality
   - Focus on the main classes and functions
   - Prioritize the most frequently used parts

2. `repomap/utils.py` (215 missing lines)
   - Continue improving the test coverage
   - Focus on the helper functions

### Medium Priority

3. `repomap/section_splitting.py` (245 missing lines)
   - Create tests for the splitting logic
   - Ensure all branches are covered

### Lower Priority

4. `repomap/api.py` (46 missing lines)
   - Create tests for the API interface

5. `repomap/install_queries.py` (46 missing lines)
   - Fix issues with the current tests

## Strategy

1. Start by focusing on testing the core functionality in `repomap.py` which has the most missing lines.
2. Continue improving test coverage for `utils.py` which contains reusable components.
3. Implement tests for `section_splitting.py` which handles an important part of the application.
4. Complete tests for the remaining modules.

## Notes

- The script `run_coverage.sh` has been updated to use unittest for test discovery and to report progress towards the 80% goal.
- Some modules with complex functionality like `repomap.py` may be more challenging to test due to dependencies.
- Consider using more mocks and controlled test environments to isolate components for testing.