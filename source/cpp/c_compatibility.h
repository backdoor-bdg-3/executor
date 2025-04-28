// c_compatibility.h - Simplified compatibility header for C files
// This file is used by C files that need Lua compatibility but can't include C++ headers
#pragma once

// Include only standard C headers
#include <stddef.h>
#include <stdarg.h>

// Include the Luau/Lua headers directly
#include "lua.h"
#include "lauxlib.h"
#include "lualib.h"

#ifdef __cplusplus
extern "C" {
#endif

// Make sure LUA_TVECTOR is defined (Luau-specific type for Vector3, etc.)
#ifndef LUA_TVECTOR
#define LUA_TVECTOR 10
#endif

// Luau userdata type
#ifndef LUA_TUSERDATA0
#define LUA_TUSERDATA0 11
#endif

// Compatibility for Luau vector operations
#if !defined(LUA_VMOVE) && !defined(LUA_VROT)
#define LUA_VMOVE 0
#define LUA_VROT 1
#define LUA_VSTEP 2
#define LUA_VSCALE 3
#define LUA_VOP_COUNT 4
#endif

// Add some compatibility macros for older Lua versions if needed
#ifndef lua_pushcfunction
#define lua_pushcfunction(L, f) lua_pushcclosure(L, (f), 0)
#endif

// Ensure new_lib is defined for library creation
#ifndef new_lib
#define new_lib(L, l) (lua_createtable(L, 0, sizeof(l)/sizeof((l)[0]) - 1), luaL_setfuncs(L, l, 0))
#endif

// For older Lua versions
#if LUA_VERSION_NUM < 502
// For Lua 5.1 compatibility
#define luaL_setfuncs(L, l, nup) luaL_register(L, NULL, l)
#endif

// Helper for luaL_checkstring across Lua versions
#if !defined(luaL_checkstring) && !defined(LUAI_FUNC)
#define luaL_checkstring(L, n) luaL_checklstring(L, (n), NULL)
#endif

// For older Lua versions, provide lua_rawlen compatibility
#if LUA_VERSION_NUM < 502 && !defined(lua_rawlen)
#define lua_rawlen(L, i) lua_objlen(L, (i))
#endif

// Useful for Roblox script execution in C
inline int luau_loadbuffer(lua_State* L, const char* buff, size_t sz, const char* name, const char* mode) {
#ifdef LUAU_FASTINT_SUPPORT
    // Use Luau's enhanced loader if available 
    return luau_load(L, name, buff, sz, mode);
#else
    // Fall back to standard Lua
    return luaL_loadbuffer(L, buff, sz, name);
#endif
}

#ifdef __cplusplus
}
#endif
