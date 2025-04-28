# Makefile for iOS Roblox Executor
# Enhanced with improved compiler output and code quality tools

# Compiler and flags
CXX := clang++
CC := clang
OBJCXX := clang++
AR := ar

# Build type (Debug or Release)
BUILD_TYPE ?= Release
# iOS SDK settings
SDK ?= $(shell xcrun --sdk iphoneos --show-sdk-path)
ARCHS ?= arm64
MIN_IOS_VERSION ?= 15.0

# Basic flags
ifeq ($(BUILD_TYPE),Debug)
    OPT_FLAGS := -g -O0
    DEFS := -DDEBUG_BUILD=1
else
    OPT_FLAGS := -O3 
    DEFS := -DPRODUCTION_BUILD=1
endif

# Use colored/enhanced output if the terminal supports it
COLORIZE_OUTPUT := 1
ifeq ($(COLORIZE_OUTPUT),1)
    # Determine if we can use the pretty output formatter
    FORMATTER := $(shell command -v python3 >/dev/null 2>&1 && echo "| ./tools/format_compiler_output.py")
endif

# Check if clang-tidy and clang-format are available
HAVE_CLANG_TIDY := $(shell command -v clang-tidy >/dev/null 2>&1 && echo 1 || echo 0)
HAVE_CLANG_FORMAT := $(shell command -v clang-format >/dev/null 2>&1 && echo 1 || echo 0)

# Static analysis flags - enable clang warnings
STATIC_ANALYSIS_FLAGS := -Wshadow -Wpointer-arith -Wuninitialized
STATIC_ANALYSIS_FLAGS += -Wconditional-uninitialized -Wextra-tokens

# Check if CI_BUILD was passed externally
ifdef CI_BUILD
    CI_FLAG := -DCI_BUILD=1
else
    CI_FLAG :=
endif

# Add compiler flags for improved diagnostics
CXXFLAGS := -std=c++17 -fPIC $(OPT_FLAGS) -Wall -Wextra -fvisibility=hidden -ferror-limit=0 -fno-limit-debug-info
CXXFLAGS += -fdiagnostics-color=always -fdiagnostics-show-category=name -fdiagnostics-absolute-paths
CXXFLAGS += $(STATIC_ANALYSIS_FLAGS) $(CI_FLAG)

CFLAGS := -fPIC $(OPT_FLAGS) -Wall -Wextra -fvisibility=hidden -ferror-limit=0 -fno-limit-debug-info
CFLAGS += -fdiagnostics-color=always -fdiagnostics-show-category=name -fdiagnostics-absolute-paths
CFLAGS += $(CI_FLAG)

OBJCXXFLAGS := -std=c++17 -fPIC $(OPT_FLAGS) -Wall -Wextra -fvisibility=hidden -ferror-limit=0 -fno-limit-debug-info
OBJCXXFLAGS += -fdiagnostics-color=always -fdiagnostics-show-category=name -fdiagnostics-absolute-paths
OBJCXXFLAGS += $(STATIC_ANALYSIS_FLAGS) $(CI_FLAG)

LDFLAGS := -shared

# Define platform
UNAME_S := $(shell uname -s)
ifeq ($(UNAME_S),Darwin)
    IS_APPLE := 1
    # iOS-specific compiler flags
    CXXFLAGS += -isysroot $(SDK) -arch $(ARCHS) -mios-version-min=$(MIN_IOS_VERSION)
    CFLAGS += -isysroot $(SDK) -arch $(ARCHS) -mios-version-min=$(MIN_IOS_VERSION)
    OBJCXXFLAGS += -isysroot $(SDK) -arch $(ARCHS) -mios-version-min=$(MIN_IOS_VERSION)
    CXXFLAGS += -fobjc-arc
    OBJCXXFLAGS += -fobjc-arc
    LDFLAGS += -dynamiclib
endif

# iOS-specific settings
ifdef IS_APPLE
    FRAMEWORKS := -framework Foundation -framework UIKit -framework Security -framework CoreData
    SYSTEM_NAME := $(shell test -d /Applications/Xcode.app && echo "iOS" || echo "macOS")
    ifeq ($(SYSTEM_NAME),iOS)
        CXXFLAGS += -mios-version-min=13.0 -fembed-bitcode
        CFLAGS += -mios-version-min=13.0 -fembed-bitcode
        OBJCXXFLAGS += -mios-version-min=13.0 -fembed-bitcode
    endif
else
    FRAMEWORKS :=
endif

# Feature flags
USE_DOBBY := 1
USE_LUAU := 1
ENABLE_AI_FEATURES := 1
ENABLE_ADVANCED_BYPASS := 1

# Define directories
ROOT_DIR := .
VM_DIR := $(ROOT_DIR)/VM
SOURCE_DIR := $(ROOT_DIR)/source
CPP_DIR := $(SOURCE_DIR)/cpp
VM_SRC_DIR := $(VM_DIR)/src
VM_INCLUDE_DIR := $(VM_DIR)/include

# Include paths
INCLUDES := -I$(VM_INCLUDE_DIR) -I$(VM_SRC_DIR) -I$(SOURCE_DIR) -I$(CPP_DIR) -I$(ROOT_DIR)

# Preprocessor definitions
DEFS += -DUSE_LUAU=1 -DLUAU_FASTINT_SUPPORT=1 -DUSE_LUA=1 -DENABLE_ERROR_REPORTING=1 -DENABLE_ANTI_TAMPER=1

# Add Luau/VM-specific defines - use single quotes to avoid shell interpretation issues
VM_DEFS := '-DLUAU_LIKELY(x)=__builtin_expect(!!(x), 1)' \
           '-DLUAU_UNLIKELY(x)=__builtin_expect(!!(x), 0)' \
           '-DLUA_SIGNATURE="\\033Lua"' \
           '-DLUA_MASKCOUNT=LUA_MASKCALL' \
           '-Dluaopen_base=luaL_openlibs' \
           '-DLBC_CONSTANT_NUMBER=Luau::LBC_CONSTANT_NUMBER' \
           '-DLBC_CONSTANT_STRING=Luau::LBC_CONSTANT_STRING' \
           '-DLBC_CONSTANT_IMPORT=Luau::LBC_CONSTANT_IMPORT' \
           '-DLBC_CONSTANT_TABLE=Luau::LBC_CONSTANT_TABLE' \
           '-DLBC_CONSTANT_CLOSURE=Luau::LBC_CONSTANT_CLOSURE' \
           '-DLBC_CONSTANT_VECTOR=Luau::LBC_CONSTANT_VECTOR' \
           '-DluaL_error=luaL_error' \
           '-DluaL_loadbuffer=luaL_loadbufferx'

ifdef USE_DOBBY
    DEFS += -DUSE_DOBBY=1
endif

ifdef IS_APPLE
    DEFS += -D__APPLE__=1
    ifeq ($(SYSTEM_NAME),iOS)
        DEFS += -DIOS_TARGET=1 -DIOS_BUILD=1 -DSHOW_ALL_WARNINGS=1
    endif
endif

# Find VM sources
VM_SOURCES := $(wildcard $(VM_SRC_DIR)/*.cpp)
VM_OBJECTS := $(VM_SOURCES:.cpp=.o)

# Main library sources 
LIB_CPP_SOURCES := $(SOURCE_DIR)/library.cpp
LIB_C_SOURCES := $(SOURCE_DIR)/lfs.c
LIB_OBJECTS := $(LIB_CPP_SOURCES:.cpp=.o) $(LIB_C_SOURCES:.c=.o)

# Find all cpp sources for roblox_execution
EXEC_CPP_SOURCES := $(shell find $(CPP_DIR) -name "*.cpp" -not -path "$(CPP_DIR)/ios/*" -not -path "$(CPP_DIR)/tests/*")
EXEC_OBJECTS := $(EXEC_CPP_SOURCES:.cpp=.o)

# iOS-specific sources
iOS_CPP_SOURCES :=
iOS_MM_SOURCES :=
ifdef IS_APPLE
    # For CI builds, exclude problematic files
    ifeq ($(CI_BUILD),1)
        # Only include the basic iOS files, avoid AI features and advanced bypass
        iOS_CPP_SOURCES += $(shell find $(CPP_DIR)/ios -maxdepth 1 -name "*.cpp" 2>/dev/null)
        iOS_MM_SOURCES += $(shell find $(CPP_DIR)/ios -maxdepth 1 -name "*.mm" 2>/dev/null)
        # Add UI files which are needed
        iOS_CPP_SOURCES += $(shell find $(CPP_DIR)/ios/ui -name "*.cpp" 2>/dev/null)
        iOS_MM_SOURCES += $(shell find $(CPP_DIR)/ios/ui -name "*.mm" 2>/dev/null)
    else
        # Regular build - include all files
        iOS_CPP_SOURCES += $(shell find $(CPP_DIR)/ios -name "*.cpp" 2>/dev/null)
        iOS_MM_SOURCES += $(shell find $(CPP_DIR)/ios -name "*.mm" 2>/dev/null)
        
        ifdef ENABLE_AI_FEATURES
            iOS_CPP_SOURCES += $(shell find $(CPP_DIR)/ios/ai_features -name "*.cpp" 2>/dev/null)
            iOS_MM_SOURCES += $(shell find $(CPP_DIR)/ios/ai_features -name "*.mm" 2>/dev/null)
        endif
        
        ifdef ENABLE_ADVANCED_BYPASS
            iOS_CPP_SOURCES += $(shell find $(CPP_DIR)/ios/advanced_bypass -name "*.cpp" 2>/dev/null)
            iOS_MM_SOURCES += $(shell find $(CPP_DIR)/ios/advanced_bypass -name "*.mm" 2>/dev/null)
        endif
    endif
endif

iOS_CPP_OBJECTS := $(iOS_CPP_SOURCES:.cpp=.o)
iOS_MM_OBJECTS := $(iOS_MM_SOURCES:.mm=.o)

# Combine objects for roblox_execution static library
ROBLOX_EXEC_OBJECTS := $(EXEC_OBJECTS) $(iOS_CPP_OBJECTS) $(iOS_MM_OBJECTS)

# Output files
STATIC_LIB := lib/libroblox_execution.a
DYLIB := lib/mylibrary.dylib

# Dobby handling
ifdef USE_DOBBY
    DOBBY_INCLUDE := -I$(ROOT_DIR)/external/dobby/include
    DOBBY_LIB := -L$(ROOT_DIR)/external/dobby/lib -ldobby
    INCLUDES += $(DOBBY_INCLUDE)
endif

# Main rule - build everything
all: directories $(STATIC_LIB) $(DYLIB)

# Check if our tools are available
check-tools:
	@echo "Checking build tools..."
	@if [ ! -x ./tools/format_compiler_output.py ]; then \
		echo "  ⚠️  Warning: format_compiler_output.py is not executable. Run 'chmod +x ./tools/format_compiler_output.py' to fix."; \
	fi
	@if [ ! -x ./tools/format_code.py ]; then \
		echo "  ⚠️  Warning: format_code.py is not executable. Run 'chmod +x ./tools/format_code.py' to fix."; \
	fi
	@if [ ! -x ./tools/run-clang-tidy.py ]; then \
		echo "  ⚠️  Warning: run-clang-tidy.py is not executable. Run 'chmod +x ./tools/run-clang-tidy.py' to fix."; \
	fi
	@if [ $(HAVE_CLANG_FORMAT) -eq 0 ]; then \
		echo "  ⚠️  Warning: clang-format not found. Code formatting will be unavailable."; \
	fi
	@if [ $(HAVE_CLANG_TIDY) -eq 0 ]; then \
		echo "  ⚠️  Warning: clang-tidy not found. Static analysis will be unavailable."; \
	fi

# Create necessary directories
directories:
	@mkdir -p lib

# Build static library
$(STATIC_LIB): $(ROBLOX_EXEC_OBJECTS)
	$(AR) rcs $@ $^ $(FORMATTER)

# Build dynamic library
$(DYLIB): $(VM_OBJECTS) $(LIB_OBJECTS) $(STATIC_LIB)
	$(CXX) $(LDFLAGS) -o $@ $(VM_OBJECTS) $(LIB_OBJECTS) -L./lib -lroblox_execution $(DOBBY_LIB) $(FRAMEWORKS) $(FORMATTER)
ifdef IS_APPLE
	@install_name_tool -id @executable_path/lib/mylibrary.dylib $@
endif

# Special compilation rules for VM files
$(VM_SRC_DIR)/%.o: $(VM_SRC_DIR)/%.cpp
	$(CXX) $(CXXFLAGS) $(INCLUDES) $(DEFS) $(VM_DEFS) -c $< -o $@ $(FORMATTER)

# Special compilation rules for C files with only basic includes
# Add VM include path explicitly and skip most other include paths for C file
$(SOURCE_DIR)/lfs.o: $(SOURCE_DIR)/lfs.c
	$(CC) $(CFLAGS) -I$(VM_INCLUDE_DIR) -I$(SOURCE_DIR) -I$(CPP_DIR) -c $< -o $@ $(FORMATTER)

# Compilation rules with colorized output
%.o: %.cpp
	$(CXX) $(CXXFLAGS) $(INCLUDES) $(DEFS) -c $< -o $@ $(FORMATTER)

%.o: %.c
	$(CC) $(CFLAGS) $(INCLUDES) $(DEFS) -c $< -o $@ $(FORMATTER)

%.o: %.mm
	$(OBJCXX) $(OBJCXXFLAGS) $(INCLUDES) $(DEFS) -c $< -o $@ $(FORMATTER)

# Clean rule
clean:
	rm -rf $(VM_OBJECTS) $(LIB_OBJECTS) $(ROBLOX_EXEC_OBJECTS) $(STATIC_LIB) $(DYLIB)
	rm -f clang-tidy-report.json
	@echo "✅ Clean completed"

# Install rule
install: all
	@mkdir -p $(ROOT_DIR)/output
	cp $(DYLIB) $(ROOT_DIR)/output/libmylibrary.dylib
	@echo "✅ Installation completed"

# Print info about build (useful for debugging)
info:
	@echo "Build Type: $(BUILD_TYPE)"
	@echo "Platform: $(UNAME_S)"
	@echo "VM Sources: $(VM_SOURCES)"
	@echo "Exec Sources: $(EXEC_CPP_SOURCES)"
	@echo "iOS CPP Sources: $(iOS_CPP_SOURCES)"
	@echo "iOS MM Sources: $(iOS_MM_SOURCES)"
	@echo "Formatter: $(FORMATTER)"
	@echo "clang-tidy: $(HAVE_CLANG_TIDY)"
	@echo "clang-format: $(HAVE_CLANG_FORMAT)"

# Code formatting and analysis rules
format-check:
	@echo "Checking code formatting..."
	@if [ $(HAVE_CLANG_FORMAT) -eq 1 ]; then \
		./tools/format_code.py --check; \
	else \
		echo "⚠️ clang-format not installed. Cannot check formatting."; \
		exit 1; \
	fi

format:
	@echo "Formatting code..."
	@if [ $(HAVE_CLANG_FORMAT) -eq 1 ]; then \
		./tools/format_code.py --fix; \
	else \
		echo "⚠️ clang-format not installed. Cannot format code."; \
		exit 1; \
	fi

auto-format:
	@if [ $(HAVE_CLANG_FORMAT) -eq 1 ]; then \
		./tools/format_code.py --fix --check 2>/dev/null || true; \
	fi

analyze:
	@echo "Running static analysis with clang-tidy..."
	@if [ $(HAVE_CLANG_TIDY) -eq 1 ]; then \
		./tools/run-clang-tidy.py --all; \
	else \
		echo "⚠️ clang-tidy not installed. Cannot run static analysis."; \
		exit 1; \
	fi

fix-analysis:
	@echo "Running clang-tidy with auto-fixes..."
	@if [ $(HAVE_CLANG_TIDY) -eq 1 ]; then \
		./tools/run-clang-tidy.py --all --fix; \
	else \
		echo "⚠️ clang-tidy not installed. Cannot run static analysis."; \
		exit 1; \
	fi

# Help target
help:
	@echo "Available targets:"
	@echo "  all           - Build everything (default)"
	@echo "  clean         - Remove build artifacts"
	@echo "  install       - Install dylib to output directory"
	@echo "  info          - Print build information"
	@echo "  format-check  - Check if code is properly formatted"
	@echo "  format        - Format code using clang-format"
	@echo "  analyze       - Run static analysis with clang-tidy"
	@echo "  fix-analysis  - Run clang-tidy with automatic fixes"
	@echo ""
	@echo "Configuration variables:"
	@echo "  BUILD_TYPE=Debug|Release      - Set build type (default: Release)"
	@echo "  USE_DOBBY=0|1                 - Enable Dobby hooking (default: 1)"
	@echo "  ENABLE_AI_FEATURES=0|1        - Enable AI features (default: 1)"
	@echo "  ENABLE_ADVANCED_BYPASS=0|1    - Enable advanced bypass (default: 1)"
	@echo "  COLORIZE_OUTPUT=0|1           - Enable colorized compiler output (default: 1)"

.PHONY: all clean install directories info help check-tools \
	format-check format analyze fix-analysis auto-format
