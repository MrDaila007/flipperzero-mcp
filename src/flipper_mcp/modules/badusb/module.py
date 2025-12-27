"""BadUSB module for Flipper Zero MCP."""

from typing import Any, List, Sequence
from mcp.types import Tool, TextContent

from ..base_module import FlipperModule
from .generator import DuckyScriptGenerator
from .validator import ScriptValidator


class BadUSBModule(FlipperModule):
    """
    BadUSB module for keyboard/mouse emulation.
    
    Provides natural language → DuckyScript generation and execution.
    This is the Phase 1 reference implementation showing how modules work.
    
    Features:
    - List, read, and manage BadUSB scripts
    - Generate DuckyScript from natural language
    - Validate scripts for safety
    - Execute scripts on target device
    - Complete workflows (generate + validate + execute)
    """
    
    @property
    def name(self) -> str:
        """Module name."""
        return "badusb"
    
    @property
    def version(self) -> str:
        """Module version."""
        return "1.0.0"
    
    @property
    def description(self) -> str:
        """Module description."""
        return "BadUSB keyboard/mouse emulation with AI-powered script generation"
    
    def __init__(self, flipper_client: Any):
        """
        Initialize BadUSB module.
        
        Args:
            flipper_client: Flipper client instance
        """
        super().__init__(flipper_client)
        self.generator = DuckyScriptGenerator()
        self.validator = ScriptValidator()
        self.badusb_path = "/ext/badusb"
    
    def get_tools(self) -> List[Tool]:
        """Register BadUSB tools with MCP server."""
        return [
            Tool(
                name="badusb_list",
                description="List all BadUSB scripts stored on Flipper Zero",
                inputSchema={
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            ),
            Tool(
                name="badusb_read",
                description="Read contents of a BadUSB script",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "filename": {
                            "type": "string",
                            "description": "Script filename (e.g., 'test.txt')"
                        }
                    },
                    "required": ["filename"]
                }
            ),
            Tool(
                name="badusb_generate",
                description="Generate BadUSB DuckyScript from natural language description",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "description": {
                            "type": "string",
                            "description": "What the script should do"
                        },
                        "target_os": {
                            "type": "string",
                            "enum": ["windows", "macos", "linux"],
                            "description": "Target operating system",
                            "default": "windows"
                        },
                        "filename": {
                            "type": "string",
                            "description": "Script filename to save as",
                            "default": "ai_generated.txt"
                        }
                    },
                    "required": ["description"]
                }
            ),
            Tool(
                name="badusb_execute",
                description="Execute a BadUSB script on the target device. WARNING: This will run the script immediately!",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "filename": {
                            "type": "string",
                            "description": "Script filename to execute"
                        },
                        "confirm": {
                            "type": "boolean",
                            "description": "Must be true (safety confirmation)",
                            "default": False
                        }
                    },
                    "required": ["filename", "confirm"]
                }
            ),
            Tool(
                name="badusb_workflow",
                description="Complete workflow: generate, validate, save, and optionally execute a BadUSB script",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "description": {
                            "type": "string",
                            "description": "What the script should do"
                        },
                        "target_os": {
                            "type": "string",
                            "enum": ["windows", "macos", "linux"],
                            "description": "Target operating system",
                            "default": "windows"
                        },
                        "execute": {
                            "type": "boolean",
                            "description": "Execute after generation (requires manual confirmation)",
                            "default": False
                        }
                    },
                    "required": ["description"]
                }
            ),
        ]
    
    async def handle_tool_call(
        self, tool_name: str, arguments: Any
    ) -> Sequence[TextContent]:
        """Handle tool execution for BadUSB module."""
        
        if tool_name == "badusb_list":
            return await self._list_scripts()
        
        elif tool_name == "badusb_read":
            return await self._read_script(arguments["filename"])
        
        elif tool_name == "badusb_generate":
            return await self._generate_script(
                arguments["description"],
                arguments.get("target_os", "windows"),
                arguments.get("filename", "ai_generated.txt")
            )
        
        elif tool_name == "badusb_execute":
            return await self._execute_script(
                arguments["filename"],
                arguments.get("confirm", False)
            )
        
        elif tool_name == "badusb_workflow":
            return await self._workflow(
                arguments["description"],
                arguments.get("target_os", "windows"),
                arguments.get("execute", False)
            )
        
        return [TextContent(
            type="text",
            text=f"❌ Error: Unknown BadUSB tool '{tool_name}'"
        )]
    
    async def _list_scripts(self) -> Sequence[TextContent]:
        """List all BadUSB scripts."""
        try:
            # Check SD card availability
            sd_card_available = await self.flipper.check_sd_card_available()
            if not sd_card_available:
                return [TextContent(
                    type="text",
                    text="❌ MicroSD card is not detected or not accessible\n\n"
                         "This operation requires a MicroSD card to be installed in your Flipper Zero.\n"
                         "BadUSB scripts are stored on the SD card.\n\n"
                         "Please:\n"
                         "1. Insert a MicroSD card into your Flipper Zero\n"
                         "2. Ensure the card is properly formatted\n"
                         "3. Use 'systeminfo_get' to verify SD card status\n"
                         "4. Try again\n\n"
                         "Note: The systeminfo module can check SD card status without requiring an SD card."
                )]
            
            files = await self.flipper.storage.list(self.badusb_path)
            
            if not files:
                return [TextContent(
                    type="text",
                    text=f"📁 No BadUSB scripts found in {self.badusb_path}\n\n"
                         "Use 'badusb_generate' to create new scripts."
                )]
            
            result = f"📁 BadUSB Scripts ({len(files)}):\n\n"
            for f in files:
                result += f"  • {f}\n"
            
            return [TextContent(type="text", text=result)]
            
        except Exception as e:
            return [TextContent(
                type="text",
                text=f"❌ Error listing scripts: {str(e)}"
            )]
    
    async def _read_script(self, filename: str) -> Sequence[TextContent]:
        """Read script contents."""
        try:
            # Check SD card availability
            sd_card_available = await self.flipper.check_sd_card_available()
            if not sd_card_available:
                return [TextContent(
                    type="text",
                    text="❌ MicroSD card is not detected or not accessible\n\n"
                         "This operation requires a MicroSD card to be installed in your Flipper Zero.\n"
                         "BadUSB scripts are stored on the SD card.\n\n"
                         "Please:\n"
                         "1. Insert a MicroSD card into your Flipper Zero\n"
                         "2. Ensure the card is properly formatted\n"
                         "3. Use 'systeminfo_get' to verify SD card status\n"
                         "4. Try again\n\n"
                         "Note: The systeminfo module can check SD card status without requiring an SD card."
                )]
            
            path = f"{self.badusb_path}/{filename}"
            content = await self.flipper.storage.read(path)
            
            return [TextContent(
                type="text",
                text=f"📄 Contents of {filename}:\n\n```duckyscript\n{content}\n```"
            )]
            
        except Exception as e:
            return [TextContent(
                type="text",
                text=f"❌ Error reading script: {str(e)}"
            )]
    
    async def _generate_script(
        self, description: str, target_os: str, filename: str
    ) -> Sequence[TextContent]:
        """Generate and save BadUSB script."""
        try:
            # Check SD card availability
            sd_card_available = await self.flipper.check_sd_card_available()
            if not sd_card_available:
                return [TextContent(
                    type="text",
                    text="❌ MicroSD card is not detected or not accessible\n\n"
                         "This operation requires a MicroSD card to be installed in your Flipper Zero.\n"
                         "BadUSB scripts must be saved to the SD card.\n\n"
                         "Please:\n"
                         "1. Insert a MicroSD card into your Flipper Zero\n"
                         "2. Ensure the card is properly formatted\n"
                         "3. Use 'systeminfo_get' to verify SD card status\n"
                         "4. Try again\n\n"
                         "Note: The systeminfo module can check SD card status without requiring an SD card."
                )]
            
            # Generate script
            script = self.generator.generate(description, target_os)
            
            # Validate for safety
            is_valid, error = self.validator.validate(script)
            if not is_valid:
                return [TextContent(
                    type="text",
                    text=f"❌ Script validation failed: {error}\n\n"
                         f"Generated script:\n```duckyscript\n{script}\n```"
                )]
            
            # Save to Flipper
            path = f"{self.badusb_path}/{filename}"
            await self.flipper.storage.write(path, script)
            
            result = f"✅ BadUSB script generated: {filename}\n\n"
            result += f"📝 Description: {description}\n"
            result += f"💻 Target OS: {target_os}\n"
            if error:  # Warnings
                result += f"\n{error}\n"
            result += f"\n📄 Script:\n```duckyscript\n{script}\n```"
            
            return [TextContent(type="text", text=result)]
            
        except Exception as e:
            return [TextContent(
                type="text",
                text=f"❌ Error generating script: {str(e)}"
            )]
    
    async def _execute_script(
        self, filename: str, confirm: bool
    ) -> Sequence[TextContent]:
        """Execute BadUSB script."""
        if not confirm:
            return [TextContent(
                type="text",
                text="❌ Execution blocked: 'confirm' parameter must be true\n\n"
                     "⚠️  WARNING: This will execute the script immediately!\n"
                     "Make sure the target device is ready and you understand what the script does."
            )]
        
        try:
            # Check SD card availability
            sd_card_available = await self.flipper.check_sd_card_available()
            if not sd_card_available:
                return [TextContent(
                    type="text",
                    text="❌ MicroSD card is not detected or not accessible\n\n"
                         "This operation requires a MicroSD card to be installed in your Flipper Zero.\n"
                         "BadUSB scripts are stored on the SD card and must be accessible to execute.\n\n"
                         "Please:\n"
                         "1. Insert a MicroSD card into your Flipper Zero\n"
                         "2. Ensure the card is properly formatted\n"
                         "3. Use 'systeminfo_get' to verify SD card status\n"
                         "4. Try again\n\n"
                         "Note: The systeminfo module can check SD card status without requiring an SD card."
                )]
            
            path = f"{self.badusb_path}/{filename}"
            
            # Read script first (for display)
            content = await self.flipper.storage.read(path)
            
            # Execute
            success = await self.flipper.app.launch("BadUsb", path)
            
            result = f"⚡ Executing: {filename}\n\n"
            result += f"📄 Script:\n```duckyscript\n{content}\n```\n\n"
            
            if success:
                result += (
                    "✅ BadUSB app launch request sent.\n\n"
                    "⚠️  Important:\n"
                    "- BadUSB may switch the Flipper’s USB mode to HID, which can disconnect the USB serial/RPC session.\n"
                    "- If you don’t see keystrokes, open **BadUSB** on the Flipper manually and run the script from the device UI.\n"
                )
            else:
                result += (
                    "❌ Could not launch BadUSB app via RPC.\n\n"
                    "Try:\n"
                    "- Ensure the Flipper is connected and unlocked\n"
                    "- Then launch **BadUSB** manually on the device and select the script\n"
                )
            
            return [TextContent(type="text", text=result)]
            
        except Exception as e:
            return [TextContent(
                type="text",
                text=f"❌ Error executing script: {str(e)}"
            )]
    
    async def _workflow(
        self, description: str, target_os: str, execute: bool
    ) -> Sequence[TextContent]:
        """Complete workflow: generate, validate, save, and optionally execute."""
        try:
            # Check SD card availability first
            sd_card_available = await self.flipper.check_sd_card_available()
            if not sd_card_available:
                return [TextContent(
                    type="text",
                    text="❌ MicroSD card is not detected or not accessible\n\n"
                         "This operation requires a MicroSD card to be installed in your Flipper Zero.\n"
                         "BadUSB scripts must be saved to the SD card.\n\n"
                         "Please:\n"
                         "1. Insert a MicroSD card into your Flipper Zero\n"
                         "2. Ensure the card is properly formatted\n"
                         "3. Use 'systeminfo_get' to verify SD card status\n"
                         "4. Try again\n\n"
                         "Note: The systeminfo module can check SD card status without requiring an SD card."
                )]
            
            result = "🤖 BadUSB Workflow\n"
            result += "=" * 50 + "\n\n"
            
            # Step 1: Generate
            result += "📝 Step 1: Generating script...\n"
            script = self.generator.generate(description, target_os)
            result += f"   ✓ Generated {len(script)} characters\n\n"
            
            # Step 2: Validate
            result += "🔍 Step 2: Validating...\n"
            is_valid, error = self.validator.validate(script)
            
            if not is_valid:
                result += f"   ❌ Validation failed: {error}\n\n"
                result += f"Generated script:\n```duckyscript\n{script}\n```"
                return [TextContent(type="text", text=result)]
            
            result += "   ✅ Valid"
            if error:  # Warnings
                result += f" (with warnings: {error})"
            result += "\n\n"
            
            # Step 3: Save
            result += "💾 Step 3: Saving...\n"
            filename = "ai_workflow.txt"
            path = f"{self.badusb_path}/{filename}"
            await self.flipper.storage.write(path, script)
            result += f"   ✓ Saved as {filename}\n\n"
            
            # Step 4: Execute (optional)
            if execute:
                result += "⚡ Step 4: Executing...\n"
                result += "   ⚠️  NOTE: Execution requires manual confirmation for safety\n"
                result += "   Use 'badusb_execute' with confirm=true to run\n\n"
            else:
                result += "⏭️  Step 4: Execution skipped (execute=false)\n\n"
            
            result += "=" * 50 + "\n"
            result += f"📄 Generated Script:\n```duckyscript\n{script}\n```\n\n"
            result += "💡 Next steps:\n"
            result += f"   • Review the script above\n"
            result += f"   • Use 'badusb_execute' to run: badusb_execute(filename='{filename}', confirm=true)\n"
            result += f"   • Or edit manually on Flipper Zero\n"
            
            return [TextContent(type="text", text=result)]
            
        except Exception as e:
            return [TextContent(
                type="text",
                text=f"❌ Error in workflow: {str(e)}"
            )]
    
    def requires_sd_card(self) -> bool:
        """BadUSB module requires SD card to store and execute scripts."""
        return True
    
    def validate_environment(self) -> tuple[bool, str]:
        """Check if BadUSB is available."""
        # In production, could check firmware version, BadUSB app presence, etc.
        # Note: We don't check SD card here because modules should still load
        # even if SD card is missing - they'll check at operation time
        return True, ""
    
    def get_dependencies(self) -> List[str]:
        """BadUSB has no module dependencies."""
        return []
    
    async def on_load(self) -> None:
        """Called when module is loaded."""
        # Could perform initialization here
        pass
    
    async def on_unload(self) -> None:
        """Called when module is unloaded."""
        # Could perform cleanup here
        pass
