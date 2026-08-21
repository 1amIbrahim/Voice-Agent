# TASK: BUILD A CINEMATIC JARVIS-STYLE AI COMMAND CENTER

You are working on an existing React application.

Your task is to transform the application into a **cinematic AI command center** centered around a sophisticated real-time 3D holographic intelligence visualization.

The uploaded reference image is the **primary visual reference** for the central holographic visualization.

Study the reference image carefully before implementing anything.

Do not merely create a generic interpretation of the words "JARVIS UI."

The uploaded image defines the target visual direction.

---

# 1. PRIMARY OBJECTIVE

Build an immersive AI interface where the central visual object looks like a:

> **Volumetric holographic intelligence environment suspended inside an implied spherical space, containing a mechanical central intelligence lens, fragmented structural geometry, radiating data pathways, dense particle fields, and cinematic depth.**

The central visualization is the identity of the application.

It is not a decorative background element.

It is not a generic AI orb.

It is not a glowing sphere.

It is a live visual representation of an intelligent system.

The surrounding interface should feel as though it exists around and responds to this central intelligence.

---

# 2. REFERENCE IMAGE ANALYSIS

The uploaded reference image contains several essential visual characteristics.

These characteristics must be reproduced conceptually and procedurally.

## 2.1 Overall form

The visualization appears spherical, but it is NOT a normal rendered sphere.

There should NOT be:

* A solid sphere
* A glass sphere
* A glowing sphere
* A perfect wireframe sphere
* A smooth gradient orb

Instead, the spherical form should be **implied** by the distribution of fragmented holographic structures.

Think of the visualization as:

```text
AN INVISIBLE SPHERICAL VOLUME

inside which exist:

- particles
- structural lines
- fragmented geometry
- radial connections
- holographic information
- mechanical structures
```

The viewer perceives a sphere because the information occupies a spherical volume.

The sphere itself should mostly not exist as a visible object.

---

# 3. CENTRAL VISUAL MODEL

The entire central visualization should follow this conceptual architecture:

```text
                         OUTER SHELL
              fragmented holographic boundary

                     ·     ·      ·
                ╱                      ╲

          STRUCTURAL GEOMETRY      DATA NODES

                    ╲          ╱
                     ╲        ╱

                  [ CENTRAL LENS ]

                     ╱        ╲
                    ╱          ╲

              PARTICLES + DATA FLOW

                ╲                      ╱
                     ·     ·      ·

                    IMPLIED VOLUME
```

The visualization should have multiple independent layers.

Do not create one object and apply glow.

Create a complete visual ecosystem.

---

# 4. TECHNICAL STACK

Use the existing application architecture where possible.

For the 3D visualization, use:

* React
* TypeScript
* Three.js
* React Three Fiber
* Drei where useful
* React Three Postprocessing where useful

The recommended installation command, if the required dependencies are missing, is conceptually:

```bash
npm install three @types/three @react-three/fiber @react-three/drei @react-three/postprocessing
```

Check the existing project first.

Do not blindly overwrite package versions.

Use the existing package manager and dependency conventions.

If the project already contains Three.js or React Three Fiber dependencies, work with the existing versions unless there is a real compatibility problem.

Important compatibility consideration:

React Three Fiber versions are tied to React major versions. Verify the current project React version before changing dependencies.

---

# 5. BEFORE WRITING CODE

First inspect:

1. The existing project structure.
2. The framework and build system.
3. The current React version.
4. Existing styling architecture.
5. Existing component architecture.
6. Existing state management.
7. Existing animation libraries.
8. Existing Three.js dependencies, if any.
9. The uploaded reference image.

Do not immediately replace the existing application.

Preserve working application functionality unless the visual redesign explicitly requires changes.

Before implementation, produce a concise implementation plan containing:

```text
CURRENT ARCHITECTURE
↓
COMPONENTS TO CREATE
↓
DEPENDENCIES REQUIRED
↓
IMPLEMENTATION PHASES
↓
PERFORMANCE STRATEGY
```

Then proceed with implementation.

---

# 6. HIGH-LEVEL APPLICATION ARCHITECTURE

Create a separation between the normal React interface and the real-time visualization engine.

Use an architecture similar to:

```text
src/
│
├── components/
│   │
│   ├── command-center/
│   │   ├── CommandCenter.tsx
│   │   ├── TopStatusBar.tsx
│   │   ├── AgentMonitor.tsx
│   │   ├── SystemMonitor.tsx
│   │   ├── CommandInterface.tsx
│   │   ├── ConversationOverlay.tsx
│   │   └── EventOverlay.tsx
│   │
│   └── jarvis-core/
│       ├── JarvisCore.tsx
│       ├── JarvisScene.tsx
│       ├── CentralLens.tsx
│       ├── InnerStructures.tsx
│       ├── ParticleField.tsx
│       ├── OuterShellFragments.tsx
│       ├── StructuralConnections.tsx
│       ├── DataPulses.tsx
│       ├── FloatingFragments.tsx
│       ├── AtmosphericParticles.tsx
│       └── SceneEffects.tsx
│
├── hooks/
│   ├── useAIState.ts
│   ├── useCoreAnimation.ts
│   └── useJarvisEvents.ts
│
├── stores/
│   └── jarvisStore.ts
│
├── types/
│   └── jarvis.ts
│
└── utils/
    ├── geometry.ts
    ├── random.ts
    └── animation.ts
```

Adapt this to the existing project structure rather than blindly duplicating it.

---

# 7. THE CENTRAL JARVIS VISUALIZATION

## CRITICAL RULE

DO NOT IMPLEMENT THIS AS A SINGLE SPHERE.

The visualization must consist of multiple independent visual systems.

Use an architecture similar to:

```text
JarvisCore
│
├── CentralLens
│
├── InnerDataStructures
│
├── ParticleIntelligenceField
│
├── MajorStructuralConnections
│
├── OuterShellFragments
│
├── FloatingGeometry
│
├── DataPulseSystem
│
├── AtmosphericParticles
│
└── PostProcessing
```

Every major system should have its own geometry and animation behavior.

The whole scene must not rotate as one object.

---

# 8. CENTRAL LENS

The central object should be inspired by a:

* Mechanical lens
* Aperture
* Reactor interface
* Optical instrument
* Holographic computational nucleus

It must NOT look like:

* A glowing ball
* A simple sphere
* A gradient orb
* A flat circle
* A Siri-style visualization

The central lens should contain multiple concentric mechanical layers.

Suggested architecture:

```text
CentralLens
│
├── OuterRing
│
├── FragmentedMechanicalSegments
│
├── RotatingInnerRing
│
├── ApertureGeometry
│
├── RadialDataConnectors
│
├── CentralVoid
│
└── EnergyHalo
```

The center should have a strong circular visual structure, but the surrounding system should remain asymmetric and complex.

Conceptually:

```text
               outer structure
             ╱                 ╲

        ────────◉───────

             inner aperture

        ╲                   ╱
             radial paths
```

Use multiple rings at slightly different depths.

Some rings should:

* Rotate slowly clockwise.
* Rotate slowly counterclockwise.
* Be fragmented.
* Contain gaps.
* Activate temporarily.

Do not make every ring a perfect circle.

Use a combination of:

* Circles
* Partial arcs
* Broken circular segments
* Polygonal segments

---

# 9. CENTRAL LENS DEPTH

The central lens should have genuine depth.

Do not stack all rings on the same Z plane.

Example conceptual depth:

```text
CAMERA

    FRONT RING
        ↓
    APERTURE SEGMENTS
        ↓
    CENTRAL VOID
        ↓
    INNER ENERGY
        ↓
    REAR STRUCTURAL RING
        ↓
    BACKGROUND PARTICLES
```

The viewer should perceive the core as an object with volume.

Some components should partially occlude others.

---

# 10. IMPLIED SPHERICAL VOLUME

The central environment should occupy an implied sphere.

Use a mathematical spherical distribution for placing:

* Outer fragments
* Nodes
* Structural geometry
* Particles
* Connection endpoints

However, do not render a visible sphere.

The visual silhouette should be incomplete.

For example:

```text
GOOD

      · · ── ·
   ╱              ╲
  ·                ·
     \          /
         CORE
     /          \
  ·                ·
   ╲              ╱
      · ── · ·


BAD

       ╭────────╮
     ╱            ╲
    │ PERFECT      │
    │ SPHERE       │
     ╲            ╱
       ╰────────╯
```

Only reveal enough information for the brain to infer a spherical boundary.

---

# 11. OUTER SHELL FRAGMENTS

Create fragmented holographic geometry around the implied spherical boundary.

These should resemble:

* Technical fragments
* Mapping-like lines
* Broken topology
* Incomplete polygons
* Coordinate paths
* Data outlines

The outer shell should NOT be a wireframe sphere.

Generate many independent fragments distributed around a spherical region.

Each fragment may be:

* A short line
* A polyline
* A small irregular polygon
* A partial arc
* A node cluster

Recommended visual behavior:

* Different opacity
* Different brightness
* Slight independent movement
* Some sections fading in and out
* Occasional activation pulses

The shell should look partially constructed, partially observed, and partially generated.

---

# 12. STRUCTURAL DATA PATHWAYS

One of the strongest visual features should be large structural pathways connecting the central lens to distant points.

Create approximately 20–50 major connections depending on visual density and performance.

Conceptually:

```text
                    OUTER NODE
                        ●
                       /
                      /
                     /
              [ CENTRAL LENS ]
                  /    \
                 /      \
                ●        ●
```

Connections should not all be straight.

Use a mixture of:

* Straight segments
* Slightly curved paths
* Multi-segment paths
* Broken paths
* Angular paths

Each path should have a relationship to a real node or fragment.

Do not add random decorative lines with no structure.

---

# 13. DATA PULSES

Animate small energy pulses along selected structural paths.

Example:

```text
CENTRAL CORE ───────●──────●──────► OUTER NODE
                         ↑
                    moving pulse
```

Pulses should:

* Start from the core during execution.
* Return toward the core when results arrive.
* Move outward for tool calls or agent dispatch.
* Move inward for incoming information.

Do not activate every connection simultaneously.

Use selective activity.

The visualization should feel intelligent rather than noisy.

---

# 14. PARTICLE INTELLIGENCE FIELD

Create a dense field of small particles distributed throughout the inner volume.

These particles should not form a perfect sphere.

Use:

* Dense clusters
* Sparse regions
* Empty gaps
* Radial concentrations
* Slight asymmetry

The particle field should feel like:

> A cloud of computational activity suspended inside a holographic volume.

Particles should vary in:

* Size
* Brightness
* Opacity
* Movement speed

Do not use thousands of individual React components.

Use efficient Three.js buffer geometry.

Where appropriate, use:

```text
THREE.BufferGeometry
+
BufferAttributes
+
ShaderMaterial or PointsMaterial
```

For continuous animation, mutate GPU-friendly or Three.js object state inside the render loop rather than triggering React state updates every frame.

---

# 15. PARTICLE MOVEMENT

Particle movement should be subtle.

Avoid:

* Chaotic explosions
* Constant rapid random motion
* All particles orbiting identically
* Perfect circular motion

Instead combine:

* Slow drift
* Local orbital motion
* Attraction toward active nodes
* Short bursts during events
* Temporary convergence

The result should resemble a living information field.

---

# 16. FLOATING INTERNAL GEOMETRY

The inner volume should contain multiple scales of geometry.

## Micro scale

* Small particles
* Small points
* Tiny line fragments

## Medium scale

* Short paths
* Node clusters
* Small polygons
* Technical fragments

## Large scale

* Long structural pathways
* Large partial arcs
* Dim geometric planes

This scale contrast is essential.

The scene should not consist entirely of equally sized particles.

---

# 17. VISUAL DEPTH

The scene must feel three-dimensional.

Use:

* Foreground fragments
* Central focal object
* Mid-depth particles
* Background geometry

Some objects should be intentionally out of focus.

Conceptually:

```text
CAMERA

[ SOFT FOREGROUND FRAGMENTS ]

          [ SHARP CENTRAL LENS ]

      [ MID-DEPTH STRUCTURES ]

[ SOFT DISTANT GEOMETRY ]
```

The central lens should generally remain the sharpest visual object.

---

# 18. CAMERA

Use a perspective camera.

The camera should remain mostly stable.

Do NOT constantly orbit around the object.

Instead use extremely subtle cinematic drift.

Possible behavior:

* Small horizontal movement
* Small vertical movement
* Tiny position noise
* Very slow look-at adjustment

The camera should feel like it is observing a physical holographic object.

It should not feel like a video game camera orbiting a model.

---

# 19. CINEMATIC POSTPROCESSING

Use postprocessing with restraint.

Potential effects:

* Bloom
* Depth of field
* Vignette
* Appropriate tone mapping

The goal is cinematic depth.

The goal is NOT to blur the entire scene.

Bloom requirements:

* Fine bright details remain visible.
* The core should glow without becoming a blurry blob.
* Small structural lines should remain sharp.
* The scene should retain high-frequency visual detail.

Do not add excessive bloom.

---

# 20. COLOR SYSTEM

The uploaded reference image uses a predominantly gold/amber holographic palette.

Follow the reference.

Do not use the previous cyan palette for this implementation unless a future design change explicitly requests it.

Use a controlled palette approximately in this direction:

```text
BRIGHT ENERGY
Warm white / pale gold

PRIMARY HOLOGRAM
Amber gold

SECONDARY LIGHT
Deep gold

DIM STRUCTURES
Brown-orange

BACKGROUND
Near-black blue
```

Example starting values:

```text
bright:     #FFF3B0
highlight:  #FFD36A
primary:    #FFB000
secondary:  #D97706
dim:        #6B3A05
background: #020508
```

These are starting values, not rigid requirements.

Do not introduce:

* Purple
* Magenta
* Pink
* Rainbow gradients
* Dominant cyan
* Dominant neon green

The final visual should strongly read as:

> GOLDEN HOLOGRAPHIC INTELLIGENCE INSIDE A DARK ENVIRONMENT

---

# 21. LIGHTING

The scene should mostly appear self-illuminated.

The holographic geometry should visually produce the sense of light.

Avoid conventional bright scene lighting.

The hierarchy should be:

```text
BRIGHT CENTRAL ENERGY
        ↓
ACTIVE GOLD STRUCTURES
        ↓
SECONDARY DATA GEOMETRY
        ↓
DIM FRAGMENTS
        ↓
NEAR-BLACK ENVIRONMENT
```

The brightest region should generally be around the central lens and active data events.

---

# 22. MOTION SYSTEM

Every major visual layer must have independent animation.

## Central lens

* Slow independent ring rotation.
* Occasional mechanical alignment changes.
* Subtle energy pulse.

## Outer shell

* Slow fragment drift.
* Sections appearing and disappearing.
* Occasional activation.

## Particles

* Local movement.
* Slow drift.
* Event-driven activity.

## Structural pathways

* Normally dim.
* Brighten during data transmission.

## Data pulses

* Travel along specific pathways.
* Trigger destination activation.

Do not synchronize all animations.

The system should feel distributed.

---

# 23. AI STATE MODEL

Create a high-level visual state model.

For example:

```typescript
export type AIState =
  | "idle"
  | "listening"
  | "thinking"
  | "executing"
  | "speaking"
  | "alert"
  | "offline";
```

The visualization should react to these states.

Do not simply change colors.

Change activity patterns.

---

# 24. IDLE STATE

Visual behavior:

* Low particle activity.
* Slow ring movement.
* Dim structural pathways.
* Very occasional pulse.
* Subtle core activity.

The system should feel awake.

---

# 25. LISTENING STATE

Visual behavior:

* Central lens becomes slightly more focused.
* Input-facing structural pathways brighten.
* Particle movement subtly converges.
* Small activity increases around the core.

The system should feel attentive.

Do not dramatically scale the entire object.

---

# 26. THINKING STATE

Visual behavior:

* Internal particle activity increases.
* More local connections activate.
* Short data pulses appear.
* Central structures become slightly more active.

Thinking should feel like distributed computation.

Do NOT simply increase the rotation speed of everything.

---

# 27. EXECUTING STATE

Visual behavior:

* Major pathways activate.
* Pulses travel outward.
* Outer nodes illuminate.
* Selected fragments activate.

This represents agent dispatch and tool execution.

---

# 28. SPEAKING STATE

Visual behavior:

* Central lens subtly reacts to audio amplitude.
* Energy rhythm increases.
* Small internal activity follows speech.

Do not make the entire sphere bounce like a music visualizer.

---

# 29. EVENT ARCHITECTURE

The visual engine should eventually connect to real AI and agent events.

Design the API now.

Example:

```typescript
export type JarvisEvent =
  | {
      type: "agent_started";
      agentId: string;
    }
  | {
      type: "agent_completed";
      agentId: string;
    }
  | {
      type: "agent_failed";
      agentId: string;
    }
  | {
      type: "tool_call";
      tool: string;
    }
  | {
      type: "tool_result";
      tool: string;
    }
  | {
      type: "thinking";
      active: boolean;
    }
  | {
      type: "speaking";
      active: boolean;
      amplitude?: number;
    }
  | {
      type: "message";
      content: string;
    };
```

The architecture should be:

```text
REAL AI EVENTS
       ↓
EVENT / STATE LAYER
       ↓
HIGH-LEVEL VISUAL STATE
       ↓
VISUAL SUBSYSTEMS
       ↓
THREE.JS SCENE
```

Do not tightly couple individual UI components directly to Three.js objects.

---

# 30. SURROUNDING UI

The normal UI should surround the central visualization without overpowering it.

Create a minimal command-center environment.

The central visualization should receive approximately 40–50% of the user's visual attention.

Surrounding UI should remain secondary.

---

# 31. TOP BAR

Create a minimal floating top status area.

Left:

```text
JARVIS
● ONLINE
```

Center:

```text
COMMAND CENTER
```

Right:

```text
TIME
SYSTEM STATUS
OPERATOR
```

Do not use a heavy navigation bar.

Do not create a large opaque header.

The top UI should feel integrated into the holographic environment.

---

# 32. LEFT-SIDE AGENT MONITOR

Display active agents.

Example:

```text
ACTIVE AGENTS

● RESEARCH AGENT
  Analyzing literature corpus
  PROGRESS 82%

● CODING AGENT
  Refactoring system

○ BROWSER AGENT
  STANDBY
```

Avoid conventional large cards.

Use:

* Thin separators
* Small status indicators
* Fine typography
* Minimal borders

---

# 33. RIGHT-SIDE SYSTEM MONITOR

Display system information.

Example:

```text
SYSTEM

CPU
42%

GPU
78%

VRAM
5.2 / 6 GB

ACTIVE MODEL
LOCAL MODEL

NETWORK
CONNECTED
```

Use minimal scientific-style visual indicators.

Do not create colorful dashboard charts.

---

# 34. COMMAND INTERFACE

The bottom center should contain the primary interaction mechanism.

Structure:

```text
             subtle waveform

   [ What would you like me to do, sir? ]

        microphone      execute
```

The command input should not look like a standard SaaS text field.

Use:

* Transparent or nearly transparent background.
* Thin holographic boundaries.
* Subtle gold focus state.
* Clean typography.
* Generous spacing.

The command interface must remain accessible.

---

# 35. CONVERSATION DISPLAY

Do not use traditional chat bubbles.

Display responses as contextual holographic information.

Example:

```text
JARVIS

I have completed the requested analysis.

[ VIEW RESULTS ]   [ OPEN WORKSPACE ]
```

Conversation should:

* Appear elegantly.
* Fade in and out.
* Not permanently cover the central visualization.
* Remain readable.

---

# 36. TYPOGRAPHY

Use a restrained technical style.

Characteristics:

* Clean sans-serif.
* Thin uppercase metadata.
* Generous tracking.
* Monospace for technical values.
* Strong hierarchy.

Do not use:

* Excessive futuristic fonts.
* Unreadable decorative typography.
* Large blocks of text.

The visual should feel sophisticated rather than gimmicky.

---

# 37. BACKGROUND

Use an almost-black environment with subtle blue-black depth.

Do not use:

* A star field.
* A spaceship room.
* A city.
* A visible sci-fi laboratory.
* A busy background image.

The central hologram itself should create the environment.

The background exists to provide contrast and depth.

---

# 38. INTERACTION

Add subtle pointer interaction where appropriate.

Possible effects:

* Minor parallax.
* Slight response of foreground fragments.
* Contextual highlighting.

Do not make the central hologram follow the mouse.

The central visualization should feel stable and physically present.

---

# 39. STARTUP SEQUENCE

Create a subtle initialization sequence.

Suggested progression:

```text
01. Dark environment.

02. Small central point activates.

03. Central lens assembles.

04. Internal particles emerge.

05. Major pathways connect.

06. Outer fragments appear.

07. Peripheral UI fades in.

08. Status becomes:

    JARVIS
    ONLINE
```

The sequence should be cinematic but fast.

Target approximately 2–4 seconds.

The interface should remain usable.

---

# 40. PERFORMANCE REQUIREMENTS

Performance is important.

Target:

```text
Desktop target:
60 FPS

Acceptable under moderate load:
45 FPS minimum
```

Use:

* BufferGeometry.
* Instancing where appropriate.
* Typed arrays.
* Reused geometry.
* Reused materials where appropriate.
* `useFrame()` for animation.
* Refs for frequently changing Three.js state.

Avoid:

* Thousands of React components for particles.
* React state updates every frame.
* Recreating geometries during animation.
* Excessive allocations inside render loops.
* Excessive postprocessing.
* Rendering invisible complexity.

If adaptive quality is necessary, reduce:

1. Particle count.
2. Depth-of-field quality.
3. Fragment count.
4. Secondary visual effects.

Do not reduce the visual identity of the central lens first.

---

# 41. QUALITY SETTINGS

Consider supporting visual quality levels.

Example:

```typescript
type QualityLevel = "low" | "medium" | "high";
```

Possible scaling:

```text
LOW
- fewer particles
- reduced fragments
- simplified postprocessing

MEDIUM
- normal particles
- normal fragments
- bloom enabled

HIGH
- maximum particle density
- depth effects
- additional atmospheric detail
```

If implementing adaptive quality, detect device capability carefully and avoid disruptive quality switching during active interaction.

---

# 42. ACCESSIBILITY AND FALLBACK

The application should not completely fail when WebGL is unavailable.

Provide a graceful fallback.

The fallback can be:

* A static procedural CSS/SVG-inspired central visualization.
* A simplified 2D canvas visualization.
* A still visual state.

Do not leave a blank screen.

Respect reduced-motion preferences where practical.

---

# 43. DEVELOPMENT TOOLS

Add development controls if useful, but do not expose them in production.

It should be easy to tune:

* Particle count.
* Bloom intensity.
* Core scale.
* Camera distance.
* Fragment density.
* Animation speed.

Prefer centralized configuration.

Example:

```typescript
export const JARVIS_CONFIG = {
  particles: {
    count: 5000,
  },

  core: {
    scale: 1,
  },

  animation: {
    intensity: 1,
  },
};
```

Use a structure appropriate to the project.

Do not scatter magic numbers throughout the scene.

---

# 44. IMPLEMENTATION PHASES

Implement in this order.

## PHASE 1 — FOUNDATION

Create:

* Command-center page.
* Dark environment.
* Correct overall layout.
* React Three Fiber canvas.

Do not over-polish.

Verify that the 3D canvas integrates cleanly with the React UI.

---

## PHASE 2 — CENTRAL LENS

Build the central mechanical lens first.

Do not proceed until it has:

* Multiple layers.
* Depth.
* Independent motion.
* Strong silhouette.

At this stage, ignore most particles.

The central lens must already look visually interesting.

---

## PHASE 3 — SPATIAL ENVIRONMENT

Add:

* Implied spherical distribution.
* Outer shell fragments.
* Major structural pathways.
* Internal geometry.

Verify that the scene feels volumetric.

---

## PHASE 4 — PARTICLES

Add:

* Inner particle intelligence field.
* Ambient particles.
* Density variation.
* Local movement.

Optimize before increasing density.

---

## PHASE 5 — DATA FLOW

Add:

* Connection activation.
* Moving pulses.
* Node events.
* Core-to-shell communication.

---

## PHASE 6 — CINEMATIC PASS

Add carefully tuned:

* Bloom.
* Depth of field.
* Vignette.
* Tone mapping.
* Atmospheric depth.

Preserve sharp detail.

---

## PHASE 7 — UI INTEGRATION

Add:

* Agent monitor.
* System monitor.
* Top status.
* Command interface.
* Conversation overlay.

The UI must remain visually secondary.

---

## PHASE 8 — AI STATE INTEGRATION

Implement the state model.

Connect visual behaviors to:

* Idle.
* Listening.
* Thinking.
* Executing.
* Speaking.
* Alert.
* Offline.

---

## PHASE 9 — OPTIMIZATION

Profile the application.

Check:

* Frame rate.
* Memory usage.
* Geometry allocations.
* Render-loop allocations.
* React re-renders.

Optimize without removing the visual identity.

---

# 45. VISUAL ANTI-PATTERNS

The following are explicit failures.

DO NOT CREATE:

* A generic glowing orb.
* A single sphere with bloom.
* A purple AI orb.
* A Siri-style orb.
* A smooth gradient ball.
* A perfect wireframe globe.
* A perfectly symmetrical solar-system model.
* A cyberpunk hacker terminal.
* Matrix-style code rain.
* Random hexadecimal text everywhere.
* A standard admin dashboard.
* Large opaque cards.
* Excessive glassmorphism.
* Thick glowing borders.
* Every element glowing equally.
* A flat 2D illustration.
* One giant object rotating continuously.

If the result resembles a generic "AI dashboard," it has failed.

---

# 46. FINAL VISUAL TEST

Before considering the implementation complete, compare the result against the uploaded reference image and evaluate:

## Spatial

Does the visualization feel volumetric?

Does it feel like objects exist at different depths?

Is the spherical volume implied rather than rendered as a literal sphere?

## Central core

Does the center resemble a complex mechanical holographic lens rather than a glowing ball?

Does it have depth?

Does it have multiple independent layers?

## Complexity

Are there multiple scales of visual information?

Are there:

* micro particles?
* medium fragments?
* large structural pathways?

## Motion

Do different systems move independently?

Do data pulses have meaningful paths?

Does the system feel alive?

## Cinematic quality

Is the central lens the focal point?

Are foreground and background elements treated differently?

Does the scene have negative space?

Does the image feel more like a cinematic holographic scene than a web dashboard?

## Color

Is the holographic visual predominantly amber/gold?

Is the background dark enough for strong contrast?

Are the forbidden colors absent?

---

# 47. FINAL SUCCESS CRITERIA

The completed interface should make the user feel that they are looking at:

> A living artificial intelligence represented as a volumetric holographic computational environment.

The user should NOT think:

> This is a website with a cool glowing orb.

The intended impression is:

> This is an actual intelligence system with a physical visual presence.

The central object should be the strongest and most memorable element in the application.

The surrounding command-center UI exists to support that visual presence.

---

# 48. REQUIRED WORKING METHOD

When implementing:

1. Inspect the existing project.
2. Study the uploaded reference image.
3. Create an implementation plan.
4. Implement the central lens first.
5. Verify the lens visually.
6. Build the surrounding volumetric environment.
7. Add particles and data pathways.
8. Add cinematic rendering.
9. Integrate surrounding UI.
10. Optimize.

Do not rush directly into creating every component.

Do not substitute the difficult central visualization with a simple orb.

Do not declare the implementation complete until the central visualization has genuine volumetric complexity, depth, independent layers, and a cinematic focal structure.

If a shortcut would turn the core into a generic glowing sphere, do not take that shortcut.

The uploaded reference image is the visual quality bar for the central holographic intelligence visualization.
