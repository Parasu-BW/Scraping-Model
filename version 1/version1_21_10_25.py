import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import time
import csv
import re
import os
import json
import logging
import uuid
from collections import OrderedDict
import io
from PIL import Image
import pandas as pd
from playwright.sync_api import sync_playwright
from dotenv import load_dotenv
import google.generativeai as genai
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from functools import partial
import concurrent.futures
import threading
import shutil

# Load environment variables
load_dotenv()

# ===================================================================
# ## SECTION 1: Master Data Structures for Validation
# ===================================================================

# 'finish' has been removed from here as it will now use a dynamic search
ATTRIBUTE_ALIASES = {
    "color": ["color", "colour", "shade", "hue", "primary color", "colors", "colours", "leg color", "leg color / finish"],
    "material": ["material", "primary material", "fabric", "materials", "upholstery material", "frame material"],
    "shape": ["shape", "form", "shapes"],
    "type": ["type", "product type", "style", "chair design", "motion type"]
}

MASTER_VALUES = {
    "colors": [
        "Black", "Navy", "DarkBlue", "MediumBlue", "Blue", "DarkGreen", "Green", "Teal",
        "DarkCyan", "DeepSkyBlue", "DarkTurquoise", "MediumSpringGreen", "Lime", "SpringGreen",
        "Aqua", "Cyan", "MidnightBlue", "DodgerBlue", "LightSeaGreen", "ForestGreen", "BlackMatt",
        "SeaGreen", "DarkSlateGray", "LimeGreen", "BlackChrome", "MediumSeaGreen", "Turquoise",
        "WoodyBrown", "RoyalBlue", "SteelBlue", "CementGray", "DarkSlateBlue", "MediumTurquoise",
        "AntiqueCopper", "Indigo", "DarkOliveGreen", "CadetBlue", "CornflowerBlue", "RebeccaPurple",
        "MediumAquamarine", "DimGray", "SlateBlue", "OliveDrab", "SlateGray", "Graphite",
        "CamouflageGreen", "LightSlateGray", "MediumSlateBlue", "LawnGreen", "Chartreuse",
        "Aquamarine", "Maroon", "Purple", "AntiqueBronze", "Olive", "Gray", "SkyBlue",
        "LightSkyBlue", "BlueViolet", "DarkRed", "DarkMagenta", "DarkSeaGreen", "LightGreen",
        "MediumPurple", "DarkViolet", "Brown", "BlushGoldPVD", "PaleGreen", "DarkOrchid",
        "HeatheredGray", "YellowGreen", "Sienna", "BleakRed", "DarkGray", "Grey", "LightBlue",
        "GreenYellow", "PaleTurquoise", "Sandrift", "LightSteelBlue", "PowderBlue", "FireBrick",
        "Copper", "DarkGoldenrod", "MediumOrchid", "BrandyRose", "RosyBrown", "GoldMattPVD",
        "DarkKhaki", "Silver", "Khaki", "MediumVioletRed", "GoldDust", "Chrome", "LightGray",
        "IndianRed", "Peru", "Chocolate", "Tan", "GoldBrightPVD", "Thistle", "Orchid",
        "Goldenrod", "PaleVioletRed", "Crimson", "Gainsboro", "Plum", "BurlyWood", "LightCyan",
        "Lavender", "DarkSalmon", "Violet", "PaleGoldenrod", "LightCoral", "LightKhaki",
        "AliceBlue", "HoneyDew", "Azure", "SandyBrown", "Wheat", "Beige", "WhiteSmoke",
        "MintCream", "GhostWhite", "Salmon", "AntiqueWhite", "Linen", "LightGoldenrodYellow",
        "FullGold", "OldLace", "WhiteMatt", "Red", "Magenta", "Fuchsia", "DeepPink",
        "OrangeRed", "Tomato", "HotPink", "Coral", "DarkOrange", "LightSalmon", "Orange",
        "LightPink", "Pink", "Gold", "PeachPuff", "NavajoWhite", "Moccasin", "Bisque",
        "MistyRose", "BlanchedAlmond", "PapayaWhip", "LavenderBlush", "SeaShell", "Cornsilk",
        "LemonChiffon", "FloralWhite", "Snow", "Yellow", "Cream", "LightYellow", "Ivory",
        "White", "Multicolour"
    ],
    "materials": [
        "202 Grade - Stainless Steel","304 Grade - Stainless Steel","ABS","ABS Plastic","Acacia Wood","ACP","Acrylic","Acrylic PMMA","Aluminium","Aluminium Alloy","Aluminium Die Cast","Aluminium & Plastic","Aluminium & Polyurethane","Aluminium Powder Coated / Pre-colated GI","Aluminium & UF","Anti Mircobial","Artificial / Cultured marble","Artificial Marble","Bali Stone","Bamboo","Banana fiber paper","Batten & Conduits","Birch Ply","Birch Wood","Bitumen","Braided Rope","Brass","Brass & Glass","Brass Stud","Bronze","Cane","Canvas","Carbon Steel","Cast Bronze","Cast Iron","Cement","Ceramic","Ceramic with Plastic","Ceramic & Wood","Charcoal","Chipboard","Clay","Compact Laminate","Composite","Concrete","Copper","Corten Steel","Cotton","CPVC","CRCA","Crystal","Crystal Glass","Crystal Metal","Die Cast","Ductile Iron","Duroplast","Elastomer","Electroplated Iron","Enameled Cast Iron","Engineered Wood","Engineered Wood & Glass","Engineered Wood & Steel","Enigneered Wood","EPDM","Expanded Polystyrene","Extruded Aluminum","Fabric","Fabric & Cane","Fabric & Leather","Fabric & Metal","Fabric & Solid Wood","Faux Leather","Fiber","Fiberglass","Fiberglass Fabric","Flame-Retardant","Flame-Retardant Thermoplastic","Flexible PCB","Frosted Glass","FRP","FR polycarbonate","Galvalume","Galvanized","Galvanized Iron","Galvanized Iron Steel","Galvanized Steel","GFRG / GRG","GI Sheet","Glass","Glass & Aluminium","Glass & Leather","Glass & Metal","Glass Wool","Granite","GRC","Gun Metal","Gypsum","Half Leather","Hand blown glass","HardWood","HDHMR","HDPE","Hemlock Wood","High Density Fiberboard","HPL","IPE Wood","Iron","Jute","Laminate","Laminated Vinyl Wallpaper","Leather","Leatherette","Leather & Metal","Leather & Plastic","Lithocast","Lucite Acrylic","Marble","Marble & Resin","Marble & Steel","MDF","Medium Density Fiber","Mesh","Metal","Metal Blade","Metal & Engineered Wood","MDF & Metal", "Metal & Plastic","Metal & Wood","Mild Steel","Mineral fiber","Mineral Wool","Mosaic","Moulded","MS Body","Natural stone","Nickel","Non-Woven Polyester Fiber Acoustic Panel","Nylon","Panchalogam","Particle Board","PC.","PET","PET Fabric Panel","Pine Wood","Plaster","Plastic","Plywood","Plywood and HDMDR","Polyamide","PolyCarbonate","Polycarbonate-FR","Polycarbonate Tube","Polyester","Polyester Fiber","Polyethylene","Poly Fiber Fabric","Polyfoam","Polymer","Polymer Cast","Polypropylene","Polystyrene","Polyurethane","Polyurethane foam","Porcelain","Powdercoated Aluminum","Powder Coated MS","PPCP","PTMT","PU Gel","PU Laminate","PU Leather","PVC","PVC Laminate","PVDF (Polyvinylidene Fluoride)","Quartz","Quartzite","Rattan","Reinforced Rubber Lined (RRL)","Resin","Rigid Vinyl","Rosewood","RPE","Rubber","Sandstone","Sanitary Acrylic","Sanitary Ceramic","Sheesham Wood","Silicone","Slate Stone","Soapstone","Solid Mango Wood","Solid Wood","Solid Wood & Cane","Solid Wood & Copper","Solid Wood & Glass","Solid Wood & Jute","Solid Wood & Metal","Solid Wood & Plastic","Solid Wood & Steel","Stainless Steel","Steel","Steel & Cane","Steel & Leather","Steel & Solid Wood","Stone","Stonex","Surfex","Synthetic","Synthetic Fabric","Synthetic Leather","Synthetic Leather & Metal","Synthetic Wicker","Teak Wood","Terracotta","Terracotta Clay","Thermoplastic","Thermoset Plastic","uPVC","Urea Formaldehyde","Velvet","Veneer Wood","Vinyl","Virgin Plastic","Vitreous China","Vitrified","Wood","Wooden Beads","Wood fiber","Wood Wool","Wool","WPC","Wrought Iron","Zinc","Zinc Alloy"
    ],
    "shapes": [
        "Abstract","Arched","Asymetrical","C Shape","Curved","Custom Size","Cylindrical","Elongated","Hexagonal","L Shape","Octagon","Oval","Oval and Round","Pentagon","Quadrant","Rectangular","Round","Semi Circle","Square","Straight","Trapezoidal","Triangle","Trioval","T Shape","U Shape"
    ],
    "types": [
        "0.6/1KV single core - 1.5sq.mm to 400sq.mm cable", "10A SP Mini MCB", "12 M Box", "12M Cover Plate", "1/2 Module", "12 Module", "16A DP Mini MCB", "16A SP Mini MCB", "16M cover plate", "18 M Box", "18M Cover Plate", "1 Door Wardrobe", "1 Hole", "1 Hole Mixer", "1M Cover Plate", "1 Seater", "1 Stop Cock", "1 Way", "1 Way Bell Push", "1 Way Bell Push with Indicator", "1 Way Switch", "1 way switch with indicator", "20A DP Mini MCB", "20A Electronic Card Operated Switch", "20A Motor Starter", "20A SP Mini MCB", "25A Motor Starter", "25A SP Mini MCB", "2 Door Wardrobe", "2 Hole", "2 in 1 Hob", "2 M Box", "2M Cover Plate", "2 Module", "2 Part with 1 Door", "2 Part with 1 Sliding", "2 Piece Set", "2 Pin Socket", "2 Seater", "2 Stop Cock", "2 Way", "2 way Inlet", "2 Way Switch", "2 Way with Double Handle", "30A Key Tag", "32A DP Mini MCB", "32A Motor Starter", "32A SP Mini MCB", "3 Door Wardrobe", "3D Wall Art", "3 Hole", "3 Hole Mixer", "3 in 1 Shower Mixer", "3M Cover Plate", "3 Module", "3 Part with 1 Door", "3 Part with 1 Sliding", "3 Piece Set", "3 Pin Shuttered Socket", "3 Pin Socket", "3 Seater", "3 Way", "3 Way Inlet", "4 Door Wardrobe", "4+ Door Wardrobe", "4 Hole", "4M Cover Plate", "4 Module", "4 Part with 2 Sliding", "4 Seater", "4 Way", "4 Way Inlet", "5 Hole", "5 Pin Socket", "5 Step Fan Regulator", "5 Way", "6A DP Mini MCB", "6M Cover Plate", "6 Module", "6 piece Set", "7 Segment DB", "8 M Box", "8 M Box (H)", "8M Cover Plate", "8M (H) Cover Plate", "8 Module", "8 Module (H)", "9M Cover Plate", "Abstract", "ACB", "Acoustic Fabric", "Acoustic Mat", "Acoustic Panel/Tile", "ACP Sheet", "Acrylic Board", "Acrylic Paste", "Acrylic Primer", "Acrylic Sheet", "AC SPD", "Adaptor", "Adjustable Prop", "Air Circuit Breaker", "Air Compressor", "Air Diffusers", "Air Filters", "Airfoil Fan", "Air Release Valve", "Alarm Clock", "Anchor Fastener", "Angle", "Angular Stop Cock", "Animal and Bird", "Animal and Bird Clock", "Annunciator", "APFC Panel", "Arch Window", "Arm chair", "Artificial Ledge", "Art Panel", "Aspirating Smoke Detector", "Automatic", "Automatic and Manual", "Automatic Changeover", "Automatic Flush", "Automatic Modular Contactor", "Automatic Sliding Door System", "Automatic Transfer Switch", "Autorefractor", "Ayurvedic Massage Bed", "Baby Protection Seat", "Back Inlet", "Backless", "Bakery Trolley", "Ball Bearing Hinge", "Ball Head Rope Barrier", "Ball Valve Handle", "Barrel Chair", "Base Frame for Shower Tray", "Basketweave Pattern", "Bath and Shower Mixer", "Bath Spout", "Bath Spout with Diverter", "Bathtub Diverter", "Bathtub Drain pipe", "Bathtub Filler with Hand Shower", "Bathtub Frame", "Bathtub Headrest", "Bathtub Mixer", "Bathtub Mixer with Diverter", "Bathtub Mixer with Handshower", "Bathtub Support", "Beaded Curtain", "Beam", "Beam Lights", "Bedside Cabinet", "Bell Mouth Trap", "Belt Compressor", "Bench Set", "Bend", "Beveled Glass", "Bidet Attachment", "Bi-drum Boiler", "Billet", "Birdbath Fountain", "Bird Nest Box", "Bladeless Ceiling Fan", "Bladeless Tower Fan", "BLDC Fans", "Bluetooth Speaker", "Bollards Light", "Bolt for WC", "Bolts and Nut", "Book Rack", "Booster Pump", "Bottle Trap", "Bottom Rail", "Bowl Urinal", "Box Type Cable Tray", "Bracket", "Breech Inlet Cap", "Bucket", "Built-In", "Built-In Hob", "Built-in-Hot Tub", "Bulkhead Light", "Bullet Camera", "Bunk Bed", "Butt Hinge", "Buttweld Fittings", "Cabinet", "Cabinet Handle", "Cabinet Knob", "Camlock Coupling", "Candle Wall Light", "Cane Bed", "Canopy Bed", "Cantilever Chair", "Capsule Lift", "Cassette AC", "Cat 6", "Cavity Fixings", "Ceiling", "Ceiling fan with chandelier", "Ceiling Fan with Light", "Ceiling Rose", "Cement Primer", "Center Hole Mixer", "Centrifugal Exhauster", "Centrifugal Fan", "Ceramic", "Ceramic Fritted Glass", "Chair", "Chalk Board", "Channel", "Chest Cooler", "Chesterfield Chair", "Chesterfield Sofa", "Cheval Mirror", "Chowki", "Clamp", "Clay Slab", "Clay Tile", "Cleanroom Door", "Clear Sink", "Click Clack Waste Coupling", "Closed Cabinet", "Closed with Glass", "Closed with Seating", "Closure Cap", "Club Chair", "CNC Cut", "Coffee Table with Chair", "Coffee Table with Stool", "Cold Heading", "Coloured Pebble", "Commercial Lift", "Commercial Locker", "Concealed", "Concealed Door Closer", "Concealed Hinge", "Concealed Stop Cock", "Conference and Meeting Chair", "Conference and Meeting Table", "Conical Hanging Light", "Conventional Fire Alarm", "Convertible", "Copper Strip", "Copper Wire", "Cork Sheet", "Corner Bead", "Corner Hot Tub", "Corner Shelf", "Corner Shower Basket", "Corner Washbasin", "Cotton Candy Machine", "Countertop Hob", "Coupler", "Coupolet", "Cover", "CP Hose", "C Purlin", "CR Coil", "Crimping Tool", "C Shaped", "CT Scan", "Cuckoo Clock", "Cuplock", "Cuplock Vertical", "Curved", "Curved Glass", "Curved Shower Cubicle", "Curved Sofa", "Cutlery Organiser", "Cutter Pump", "Cylindrical Lock", "Dancing Fountain", "Dataline SPD", "Dead Bolt Lock", "Decorative Brackets", "Decorative Mirror", "Delivery Table", "Deposit Locker Cabinet", "Designer Clock", "Designer Fans", "Designer Laminate", "Diaphragm Digital", "Dichroic Film", "Diesel Engine Pump", "Digital Clock", "Dining Set with Bench", "Dining Set with Chair", "Dining Set with Stool", "Dismantling Joint", "Distemper", "Diya", "DND and MMR Indicator", "DND Switch", "Docking Door", "Dome Camera", "Door Opener", "Door profile", "Door Silencer", "Double Bar Towel Rail", "Double Bowl", "Double Bowl with Drainboard", "Double Charge Vitrified", "Double Door", "Double Door with Sidelight", "Double Flap Valve", "Double Rack Towel Rail with Hook", "Double Side Wall Clock", "Double Soap Dish", "Double Soap Dispenser", "Double Soap Tray", "Double Y", "DP Switch with Indicator", "Drainage Pump", "Drains With Trap", "Drain Valve", "Drawer Dividing Panel", "Drawer Mat", "Drawer Mount", "Dressing Cabinet", "Dressing Unit", "Dripline joiner", "Dripline Pipe", "Dripline Valve", "Dryer Holder", "Dual Flow", "Dual Fuel Burner", "Dual Soap Dispenser", "Duct AC", "Earth Rod", "Elbow", "Electric Massage Bed", "Electronic Timer Switch", "End Cap", "End Suction Pump", "Epoxy Primer", "Ergonomic Chair", "Escape Chutes", "Escutcheon", "Executive Chair", "Exposed Shower Pipe & Hand Shower", "Face Recognition", "Fancy Angle Holder", "Fancy Batten Holder", "Fandelier Ceiling Fan", "Fan Regulators", "Fan Remote", "Female adaptor", "Female Thread Adaptor", "Filing Cabinet", "Filler With Hand Shower", "Filter", "Fingerprint", "Fireclay Brick", "Fire Rated Shutter", "Fire Stand Post", "Fixed Shelf Support", "Fixing Brackets", "Fixing Clips", "Flame Retardant", "Flange", "Flap Hinge", "Flat Sheet", "Flat Weaves", "Flexible", "Flexible Conduit", "Flexible Hose", "Floor Expansion Joint", "Floor Guide", "Floor Mirror", "Floor Mount", "Floor Mounted Bowl", "Floor Mounted Bowl with Cistern", "Floor Vase", "Floral", "Floral Design", "Flush Plate", "Flush Valve", "Fluted Laminate", "Fluted Pattern", "Focus Pod", "Foldable Shelf Support", "Folding Door", "Folding Door Frame", "Folding Partition", "For Exposed Shower Pipe", "For Hand Shower", "Four Door", "Frame Anchors", "Frameless Flush Tank", "Free Standing", "Free Standing Hot Tub", "French Door", "FR LSH", "Frosted Film", "FRP Gutter", "Fryer", "Full Body Vitrified", "Full Frame Flush Tank", "Full Length Curtain", "Full Partition", "Full Pedestal", "Full Pedestal Cover", "Full Support Frame", "Gas Burner", "GI Strip", "Glass Connector", "Glass Door Knob", "Glass Gasket", "Glass Hinge", "Glass Holder", "Glass Profile", "Glass Top Sliding Door", "Glass Wall Bracket", "Glazed Vitrified - GVT", "Globe Valve", "Grade 43", "Grade 53", "Grill Shutter", "Grooved Coupling", "Grout Admixture", "Gyrostream Body Shower", "Hairdressing Trolley", "Half Frame Flush Tank", "Half Length Curtain", "Half Partition", "Half Pedestal", "Half Pedestal Cover", "Half Stall Urinal", "Hand Dryer With Paper Dispenser And Waste Bin", "Hand Knotted", "Hand Loom", "Hand Painted Clock", "Hands-In Dryer", "Hands-Under Dryer", "Hand Tufted", "Hand Braided", "Hanging Bell", "Hanging Quotes", "Hanging Tea Light Holder", "H Beam", "HDMI Socket", "Health Faucet Fixture", "Health Faucet Set", "Heat Recovery System", "Herringbone Pattern", "HFFR", "Hidden Waste Coupling", "High Alumina Brick", "High Bay Light", "High Speed Door", "High Speed Fans", "Hinge", "Hollow Bar", "Home Office Desk", "Home UPS", "Honeycomb Blind", "Hook Rack", "Horizontal", "Hose Shut Off Nozzle", "Hot Plate", "HPL Plank", "HPL Sheet", "HR Coil", "HRFR", "Hydraulic Door Closer", "Hydraulic Hinge", "Hydraulic Lift", "Hydraulic Scissor Lift", "I Beam", "Inclined", "Inclined Moving Walk", "Inclined Stair Lift", "Industrial Air Cooler", "Infrared Sauna", "Inline Pump", "Inverter Battery", "Ionization", "IPE Wood Deck", "IRIS Scanner", "Isolation Transformer", "Isolator", "Jet Spary", "Jet Sprays", "Joints", "Keratometer", "Kid's Cabinet", "Kid's Open and Closed Shelf", "Kid's Open Shelf", "Kids Room clock", "Kid's Room Clock", "Kitchen Shelves", "Kitchen Storage", "Kitchen Trolley", "Klin Formed Glass", "Knob Lock", "Laboratory Sinks", "Lace Curtain", "Ladder Cable Tray", "Ladder Towel Rail", "Laminar Jet", "Landing Valve Fitting", "Landscape", "Lantern", "Latch Lock", "Lead-Lined Door", "LED Mirror", "Leg Support Frame", "Lensometer", "Lever Handle", "Lever Handle Lock", "Lifesavior Adaptor", "Lifesavior Plug", "Line Interactive UPS", "Load Break Switch", "Long Bend", "Long Body Biptab", "Low Back", "Low Bay Light", "L Shape", "L Shape Office Desk", "L-Shape Shower Cubicle", "LT Automatic Voltage Stabilizer", "Machine Made", "Magnesia-Carbon Brick", "Magnetic Catch", "Male Adapter", "Male Connector", "Male Thread Adaptor", "Manual", "Manual Bidet Seat", "Marble Finish", "Marble Gloss Finish", "Marble Matt Finish", "Marble Pebble", "Marker Board", "MCB", "MCB Changeover", "MCB Enclosure Sheet", "MCB Indicator Light", "MCB - Miniature Circuit Breaker", "MCB Protected Power Unit", "MCCB", "Mechanical Gear Clock", "Meeting Pod", "Metal Finish", "Metal Flush Door", "Metal Primer", "Military Decor", "Mirror Set", "Mixer Cartridge", "MMR Switch", "Mobile Shelf", "Modern Wall Clock", "Modular UPS", "Monoblock Pump", "Mono Compressor", "Monument Decor", "Moroccan", "Mortise Handle", "Mortise Lock", "Mortise Lock Body", "Moulded Case Circuit Breaker", "MPCB", "MRI Scan", "MS Conduit", "Multi Flow", "Multi Function Steam Cabin", "Mural", "Musical Clock", "Nail Anchor", "Nails", "Nautical Decor", "Nightstand", "Nipolet", "Nipple", "Noise Reduction Set", "Non Return Valve", "Non-segregated phase busduct (NSPB) - MV", "Nozzle Bib Tap", "Nozzle Diffuser", "NVR", "Oil Burner", "Oil Lamp", "One and Half Bowl", "One Door", "Online UPS", "Onload Changeover Switch", "Open", "Open and Closed Cabinet", "Open and Closed with Glass", "Open Cabinet", "Open Top Bin", "Open with Seating", "O Ring", "Outdoor Sofa Set", "Outlet Drain", "Over Bend", "Overhead Door Closer", "Pan Connector", "Panel Bed", "Panel Track Blind", "Parquet Pattern", "Partition Curtain", "Patch Fitting", "Pedal Bin", "Pedestal Cabinet", "Pedestal Unit", "Peep Hole", "Pendant Light", "Pendulum Clock", "People and Places", "Perforated Cable Tray", "Peripheral Pump", "Phase Selector DB", "Phone Pod", "Photoelectric", "Photovoltaic SPD", "Pigment Dispersion", "Pigment Powder", "Pillar Tap", "Pipe Clip", "Pipe earthing", "Plain Finish", "Plain Gloss Finish", "Plain Matt Finish", "Plain Pattern", "Planter with Plant", "Plant Stand", "Plastic Deck", "Plate earthing", "Platform Bed", "Plugtop", "Plugtop With Indicator", "Polished Glazed Vitrified - PGVT", "Polystyrene Sheet", "Pond Liner", "Pooja Mandir", "Pooja Shelf", "Pool Brush & Cleaner", "Pool Cover", "Pool Ladder", "Pool Liner", "Pool Rope", "Pool Skimmer", "Pool Starting Block", "Pool Vaccum Head", "Pop Up Waste Coupling", "Porcelain", "Portable AC", "Portable Air Cooler", "Portable Bidet", "Portable Hose Pipe", "Portable Massage Bed", "Portable Speaker", "Poster Bed", "Pre Galvanized Pipe", "Premium Fan", "Pressed Water Tank", "Pressure Gauge Valve", "Prewired DB", "Private", "Propeller pump", "Protected Socket", "P Trap", "Pull Handle", "Pull Out", "Pull Out Drawer", "PU Primer", "Purlin", "PVC Conduit", "PVC Strip Curtain", "Q Manager Rope", "Q Manager Stand", "Quartz Pebble", "Queue Manager Sign Board", "Raceway Cable Tray", "Radiant Warmer", "Rain Shower", "RCA Socket", "RCBO", "RCCB", "Real Wood Deck", "Reception Chair", "Reception Desk", "Recessed Soap Tray", "Recliner", "Recliner Set", "Rectangular Office Desk", "Reducer", "Reducer Tee", "Reducing Y", "Regular Fan", "Regular Waste Coupling", "Reinforcing Rod", "Relay", "Religious", "Residential Lift", "Retinoscope", "Reverse Y", "Revolving Door", "RG11", "RG59", "RG6", "Riser with Socket", "Rising Main", "River Pebble", "RJ 11 Telephone Socket", "RJ 45 Jack With Cat 6", "Rod earthing", "Roller Blind", "Roman Blind", "Roman Numeral Wall Clock", "Roof Foam Filler", "Roof Ridge End", "Roof Ridges", "Rosette Plate", "Rotary Switch", "Round Bar", "RRL Hose", "Rubber Seal", "Saddle", "Salon Footrest", "Salon Steamer", "Sand Hourglass", "Screw", "Sculpture Fountain", "Seal Expansion Joint", "Sectional Recliner", "Sectional Sofa", "Semi-Recessed Washbasin", "Server Cabinet", "Servo stabilizer", "Shag", "Shaver Socket", "Sheet", "Shelf", "Shower Mixer with Spout", "Shower Partition for Bathtub", "Shower Screen", "Showpiece", "Side Wall Hanging Clock", "Silent Pipe", "Single Bar Towel Rail", "Single Bed", "Single Bowl", "Single Bowl with Drainboard", "Single Door", "Single Door Shower Partition", "Single Door with Sidelight", "Single Flow", "Single Line", "Single phase submersible starters", "Single Phase UPS", "Single Soap Dish", "Single Soap Dispenser", "Single Y", "Slab", "Sliding and Folding Door", "Sliding Door", "Sliding DoorFitting", "Sliding Door Frame", "Sliding Door Lock", "Sliding Door Remote Control", "Sliding Door Roller", "Sliding Door Wardrobe", "Sliding Gate Operator", "Sliding Shower Partition", "Sliding Top Track", "Slim Cap", "Slipper Chair", "Smart Ceiling Light", "Smart Curtain Switch", "Smart Door Bell", "Smart Fans", "Smart Light Dimmer", "Smart Lighting Pole", "Smart Speaker", "Smart WC", "Soap Dish with Tumbler Holder", "Soap Dispenser with Tumbler Holder", "Sofa", "Softener", "Softener Plant", "Solar Batten", "Solar Battery", "Solar Film", "Solar Off-grid Inverter", "Solar On-grid Inverter", "Solar Street Lighting", "Solenoid Valves", "Solid Bottom Cable Tray", "Soot Blower", "Speckle Pattern", "Split AC", "SPN DB", "SPN Horizontal DB", "Spot Light", "Spout", "Spout & Hand Shower", "Spout & Overhead Shower", "Sprinkler Drop", "Sprinkler Head", "Square Bar", "Square Pattern", "SRCD", "Stack Glass", "Stained Glass", "Stand", "Standard Massage Bed", "Standard Recliner", "Standard Sofa", "Standard Steam Cabin", "Steam Boiler", "Steam Box", "Steam Controller", "Steamer", "Steel Strip", "Stone Fountain", "Stone Pebble", "Stopper", "Storage Bed", "Storage Cabinet", "Strip Curtain", "Strip Light", "Strip Pattern", "Strip Roll", "Study Chair", "Submersible Sewage Pump", "Subway Tile", "Support Frame", "Surface Mounted Luminaries", "Surface Mounted Sensor Lights", "Surge Protection Adaptor", "Surge & Spike Guard", "Suspended Luminaries", "Swing Door", "Swing Door Frame", "Swing Dustbin", "Swing Gate Operator", "Swivel", "Swivel / Adjustable Towel rail", "Swivel with Footstool", "Synthetic Enamel", "Table and Chair set", "Table clock", "Table Mount", "Table Tea Light Holder", "Table Vase", "Table with Bench", "Table with Chair", "Table with Stool", "Tail Piece", "Tall Body Pillar Tap", "Tape", "Tap-off Box", "Tee", "Thermal Balancing Valve", "Thermostatic Bath and Shower Mixer", "Thermostatic Expansion Valve", "Thermostatic Shower Diverter", "Thermostatic Shower Mixer", "Threaded Curtain", "Threaded End Plug", "Threaded Rod", "Three Door", "Three Phase UPS", "Tiered Fountain", "Tie Rod", "Timber", "Time Switch", "Toilet Seat", "Tonometer", "Top Inlet", "Toran and Latkan", "Touch Fan Regulator", "Towel Rack", "Towel Rack with Hook", "Towel Rack with Rail", "Tower AC", "Tower Ladder", "TPN DB", "TPN Horizontal DB", "TPN Vertical DB", "Traditional Sauna", "Transparent Shutter", "Transport Decor", "Trim Handle for Panic Bar", "Tripod Clock", "T-Shape Shower Partition", "Turf", "TV Socket", "Two Door", "Underlight Fan", "Union", "Universal Adaptor With Indicator", "Universal Multiplug Adaptor", "Unpolished Pebble", "Upholstered Bed", "Urinal Fixing Set", "Urinal Lid", "Urinal Outlet Drain", "Urinal Spreader Back Inlet", "Urli", "Urli with Diya", "USB Charger", "USB Charger Socket", "USB Star 4+1 Surge & Spikeguard", "U Shape", "U Shape Office Desk", "U-shape Shower Cubicle", "Valley Gutter", "Venetian Blind", "Vent Cowl", "Vertical", "Vertical Blind", "Vertical Borewell Pump", "Vertical Cooler", "Vertical Freezer", "VGA Socket", "Vintage Clock", "Vintage Decor", "Vitrified", "Voltage Stabilizer", "Wall", "Wall Cistern", "Wall clock", "Wall Decor Mirror", "Wall Diffuser", "Wall Hanging", "Wall Hung Cabinet", "Wall Mount", "Wall Mounted Bowl", "Wall Mounted Bowl with Cistern", "Wall Mount Full Pedestal", "Wall Mount Half Pedestal", "Wall Mount Q Manager", "Wall Plaster", "Wall Plates", "Wall Primer", "Wall Shower Diverter", "Wall Shower Mixer", "Wall Tea Light Holder", "Wall to Wall", "Wardrobe Doors", "Washbasin Deck", "Waste Coupling", "Waste Pipe", "Water Closet Bowl", "Water Closet Bowl with Cistern", "Water Monitor", "Water Pressure Booster Pump", "Waxing Trolley", "W Beam", "Welding Curtain", "Wheel Dustbin", "Wifi Switches", "Window AC", "Window Air Cooler", "Window Curtain", "Window Film", "Wing Back Chair", "Wire Mesh Cable Tray", "With Armrest", "With Backrest", "With Base", "With Digital Display", "With Dressing Table", "With Flap", "With Footrest", "With Footstool", "With Frame", "With Hand shower Holder", "With Holder", "With Holder and Handle", "Without Armrest", "Without Backrest", "Without Base", "Without Digital Display", "Without Dressing Table", "Without Flap", "Without Footrest", "Without Frame", "Without Hand shower Holder", "Without Holder", "Without Holder and Handle", "Without Soap Dish", "Without Storage", "Without Towel Rail and Hook", "Without Trap", "Without TV Stand", "Without Writting Desk", "With Shower Hook", "With Soap Dish", "With Storage", "With Towel Bar", "With Towel Hook", "With Towel Rail", "With Towel Rail and Hook", "With Trap", "With TV Stand", "With Writting Desk", "Wooden Ceiling Fan", "Wooden Wall Clock", "Wood Finish", "Wood Flush Door", "Wood Gloss Finish", "Woodgrain Pattern", "Wood Matt Finish", "World Map", "WPC Deck", "Zebra Blind", "Zip Blind", "Z Purlin"
    ]
}

VALIDATION_SETS = {
    key: {v.lower() for v in values} for key, values in MASTER_VALUES.items()
}
# --- END of SECTION 1 ---

@dataclass
class ProductSchema:
    """Enhanced product schema for Gemini LLM extraction"""
    title: str
    price: Optional[str] = None
    original_price: Optional[str] = None
    description: Optional[str] = None
    short_description: Optional[str] = None
    brand: Optional[str] = None
    category: Optional[str] = None
    specifications: Optional[Dict[str, str]] = None
    features: Optional[List[str]] = None
    availability: Optional[str] = None
    sku: Optional[str] = None
    rating: Optional[float] = None
    review_count: Optional[int] = None
    images: Optional[List[str]] = None
    variants: Optional[List[Dict]] = None
    shipping_info: Optional[str] = None
    return_policy: Optional[str] = None
    additional_attributes: Optional[Dict[str, Any]] = None
    youtube_url: Optional[str] = None
    video_urls: Optional[List[str]] = None

class GeminiProductExtractor:
    """Product detail extractor using ONLY Google's Gemini LLM"""

    def __init__(self, api_key: str = None, model_name: str = "gemini-1.5-pro"):
        self.api_key = api_key or os.getenv("GOOGLE_AI_API_KEY")
        self.model_name = model_name
        self.model = None
        if not self.api_key:
            raise ValueError("❌ GOOGLE_AI_API_KEY is required.")
        self.setup_gemini_client()

    def setup_gemini_client(self):
        try:
            genai.configure(api_key=self.api_key)
            model_options = ["gemini-1.5-pro", "gemini-pro", "gemini-1.0-pro"]
            for model_name in model_options:
                try:
                    available_models = [m.name for m in genai.list_models()]
                    full_model_name = next((available for available in available_models if model_name in available), None)
                    if full_model_name:
                        self.model_name = full_model_name
                        self.model = genai.GenerativeModel(
                            model_name=full_model_name,
                            safety_settings=[
                                {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
                                {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
                                {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
                                {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"}
                            ]
                        )
                        print(f"✅ Gemini model initialized: {full_model_name}")
                        return
                except Exception as e:
                    print(f"⚠️ Model {model_name} failed: {e}")
                    continue
            raise Exception("No working Gemini model found")
        except Exception as e:
            print(f"❌ Failed to initialize Gemini client: {e}")
            raise

    def extract_product_details(self, html_content: str, product_url: str = None) -> ProductSchema:
        print(f"🤖 Extracting product details using Gemini {self.model_name}...")
        try:
            extraction_prompt = self._create_gemini_prompt(html_content, product_url)
            generation_config = genai.types.GenerationConfig(
                temperature=0.1, max_output_tokens=4000, candidate_count=1, top_p=0.8, top_k=20
            )
            response = self.model.generate_content(
                extraction_prompt, generation_config=generation_config, request_options={"timeout": 60}
            )
            result = self._parse_gemini_response(response)
            if result:
                product_schema = self._create_product_schema(result)
                print(f"✅ Gemini extraction successful: {product_schema.title[:50]}...")
                return product_schema
            else:
                raise Exception("Empty or invalid Gemini response")
        except Exception as e:
            print(f"❌ Gemini extraction failed: {e}")
            return self._enhanced_fallback_extraction(html_content, product_url)

    def _create_gemini_prompt(self, html_content: str, product_url: str = None) -> str:
        max_html_length = 30000
        if len(html_content) > max_html_length:
            soup = BeautifulSoup(html_content, 'html.parser')
            important_sections = []
            for script in soup.find_all("script", type="application/ld+json"): important_sections.append(str(script))
            for meta in soup.find_all("meta")[:25]: important_sections.append(str(meta))
            if soup.find("title"): important_sections.append(str(soup.find("title")))
            for h_tag in soup.find_all(["h1", "h2", "h3"])[:5]: important_sections.append(str(h_tag))
            for section in soup.find_all(class_=re.compile(r'product|item|detail', re.I))[:10]: important_sections.append(str(section)[:1000])
            truncated_content = "\n".join(important_sections) + "\n" + html_content[:max_html_length//3]
            html_content = truncated_content + "\n... [Content truncated for optimization]"

        prompt = f"""You are an expert e-commerce product data extraction specialist. Analyze the HTML content and extract comprehensive product information.

EXTRACT THESE FIELDS:
- title: Complete product name.
- price: Current price with currency.
- original_price: Original price if on sale.
- brand: The brand or manufacturer.
- category: The product category.
- description: The complete product description. Combine multiple paragraphs into a single text block. Extract the text verbatim.
- features: A list of key features (usually from bullet points).
- specifications: A dictionary of key-value technical specs (e.g., {{"Dimensions": "H 35 x W 34", "Material": "Leather", "Color": "Brown", "Shape": "Rectangle"}}).
- sku: The product's SKU or model number.
- availability: Stock status (e.g., "In Stock", "Out of Stock").
- images: All product image URLs (absolute URLs).
- youtube_url: The first YouTube embed URL found on the page.
- video_urls: A list of any other non-YouTube video URLs (e.g., .mp4, Vimeo).
- variants: Product variants like colors or sizes.
- shipping_info: Shipping details.
- return_policy: Return policy details.

OUTPUT FORMAT - Return ONLY valid JSON:
{{
    "title": "Complete product name",
    "price": "Current price with currency",
    "original_price": "Original price if on sale, null otherwise",
    "brand": "Brand name",
    "category": "Product category",
    "description": "A paragraph describing the product...",
    "features": ["Feature 1", "Feature 2"],
    "specifications": {{"spec_name": "spec_value"}},
    "availability": "In Stock/Out of Stock/Limited",
    "sku": "SKU or model number",
    "images": ["https://image-url-1.jpg", "https://image-url-2.jpg"],
    "youtube_url": "https://www.youtube.com/embed/...",
    "video_urls": ["https://site.com/video.mp4"],
    "variants": [{{"name": "Color", "options": ["Red", "Blue"]}}],
    "shipping_info": "Shipping details",
    "return_policy": "Return policy"
}}

CRITICAL RULES:
- For the `description` field, you must only extract text that exists directly in the HTML. DO NOT generate, create, author, or summarize a new description.
- The `description` field should NOT contain key-value specifications or bulleted lists that belong in `specifications` or `features`.
- For `specifications`, extract attributes like Color, Material, Shape, and Type as key-value pairs if you find them.
- Use null for missing data.

PRODUCT URL: {product_url}

HTML CONTENT:
{html_content}

Extract and return the JSON:"""
        return prompt

    def _parse_gemini_response(self, response) -> Dict:
        try:
            if not response or not response.text: return {}
            response_text = response.text.strip()
            if "```json" in response_text:
                start = response_text.find("```json") + 7
                end = response_text.rfind("```")
                if end > start: response_text = response_text[start:end].strip()
            elif response_text.startswith("```"):
                start = response_text.find("```") + 3
                end = response_text.rfind("```")
                if end > start: response_text = response_text[start:end].strip()
            start_idx = response_text.find('{')
            end_idx = response_text.rfind('}') + 1
            if start_idx >= 0 and end_idx > start_idx:
                json_str = response_text[start_idx:end_idx]
                json_str = json_str.replace('\n', ' ')
                json_str = re.sub(r',\s*([}\]])', r'\1', json_str)
                return json.loads(json_str)
            return {}
        except json.JSONDecodeError as e:
            print(f"JSON parsing error: {e}")
            return {}
        except Exception as e:
            print(f"Response parsing error: {e}")
            return {}

    def _create_product_schema(self, result: Dict) -> ProductSchema:
        return ProductSchema(
            title=result.get('title', 'Unknown Product'),
            price=result.get('price'), original_price=result.get('original_price'),
            description=result.get('description'), short_description=result.get('short_description'),
            brand=result.get('brand'), category=result.get('category'),
            specifications=result.get('specifications', {}), features=result.get('features', []),
            availability=result.get('availability'), sku=result.get('sku'),
            rating=result.get('rating'), review_count=result.get('review_count'),
            images=result.get('images', []), variants=result.get('variants', []),
            shipping_info=result.get('shipping_info'), return_policy=result.get('return_policy'),
            additional_attributes=result.get('additional_attributes', {}),
            youtube_url=result.get('youtube_url'),
            video_urls=result.get('video_urls', [])
        )

    def _enhanced_fallback_extraction(self, html_content: str, product_url: str = None) -> ProductSchema:
        print("🔧 Using enhanced fallback extraction method")
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            title = self._extract_title_fallback(soup)
            price = self._extract_price_fallback(soup)
            description = self._extract_description_fallback(soup)
            images = self._extract_images_fallback(soup, product_url)
            features = self._extract_features_fallback(soup)
            json_ld_data = self._extract_json_ld_fallback(soup)
            return ProductSchema(
                title=title, price=price, description=description, images=images, features=features,
                brand=json_ld_data.get('brand'), category=json_ld_data.get('category'),
                rating=json_ld_data.get('rating'), availability=json_ld_data.get('availability', 'Unknown'),
                additional_attributes={'extraction_method': 'enhanced_fallback', 'extraction_timestamp': datetime.now().isoformat()}
            )
        except Exception as e:
            print(f"Enhanced fallback failed: {e}")
            return ProductSchema(title="Fallback Extraction Failed", additional_attributes={'error': str(e)})

    def _extract_title_fallback(self, soup) -> str:
        selectors = ['h1.product-title', 'h1[class*="product"]', 'h1[class*="title"]', '.product-name h1', '.product-title', '[data-testid="product-title"]', 'h1', 'h2.product-title', '[itemprop="name"]']
        for selector in selectors:
            try:
                element = soup.select_one(selector)
                if element and element.get_text(strip=True) and len(element.get_text(strip=True)) > 5: return element.get_text(strip=True)
            except: continue
        meta_title = soup.find('meta', {'property': 'og:title'})
        if meta_title and meta_title.get('content'): return meta_title['content']
        if soup.title: return soup.title.string or "Unknown Product"
        return "Product Title Not Found"

    def _extract_price_fallback(self, soup) -> Optional[str]:
        selectors = ['.price-current', '.price-now', '.current-price', '.product-price', '[class*="price"]:not([class*="original"]):not([class*="old"])', '[data-testid*="price"]', '[itemprop="price"]', '.money', '.amount']
        for selector in selectors:
            try:
                for element in soup.select(selector):
                    price_match = re.search(r'[₹$€£¥]?\s*[0-9,]+\.?[0-9]*', element.get_text(strip=True))
                    if price_match: return price_match.group().strip()
            except: continue
        return None

    def _extract_description_fallback(self, soup) -> Optional[str]:
        selectors = ['.product-description', '.product-desc', '[class*="description"]', '[data-testid="product-description"]', '[itemprop="description"]', '.product-details', '.product-info']
        for selector in selectors:
            try:
                element = soup.select_one(selector)
                if element and len(element.get_text(strip=True)) > 20: return element.get_text(strip=True)[:500]
            except: continue
        meta_desc = soup.find('meta', {'name': 'description'})
        if meta_desc and meta_desc.get('content'): return meta_desc['content']
        return None

    def _extract_images_fallback(self, soup, product_url: str = None) -> List[str]:
        images = set()
        selectors = ['.product-images img', '.product-gallery img', '[class*="product-image"] img', '[data-testid*="image"] img', '.gallery img', '.slider img', '.carousel img']
        for selector in selectors:
            try:
                for img in soup.select(selector)[:10]:
                    src = img.get('src') or img.get('data-src') or img.get('data-original')
                    if src:
                        if product_url and not src.startswith('http'): src = urljoin(product_url, src)
                        if src.startswith('http') and self._is_product_image(src): images.add(src)
            except: continue
        try:
            for img in soup.find_all('img'):
                src = img.get('src') or img.get('data-src') or img.get('data-original')
                if src and self._is_product_image(src):
                    if product_url and not src.startswith('http'): src = urljoin(product_url, src)
                    if src.startswith('http'): images.add(src)
        except: pass
        return list(images)[:8]

    def _is_product_image(self, src: str) -> bool:
        if not src: return False
        skip_patterns = ['icon', 'logo', 'avatar', 'thumb', 'small', 'mini', 'badge', 'banner', 'header', 'footer', 'nav', '.svg', 'data:image', 'placeholder', 'payment', 'shipping']
        src_lower = src.lower()
        if any(pattern in src_lower for pattern in skip_patterns): return False
        product_patterns = ['product', 'item', 'gallery', 'main', 'large', 'zoom', 'variant']
        if any(pattern in src_lower for pattern in product_patterns): return True
        return True

    def _extract_features_fallback(self, soup) -> List[str]:
        features = []
        selectors = ['.features ul li', '.product-features li', '[class*="feature"] li', '.specifications li', '.highlights li']
        for selector in selectors:
            try:
                for element in soup.select(selector):
                    text = element.get_text(strip=True)
                    if text and 5 < len(text) < 200: features.append(text)
            except: continue
        return features[:10]

    def _extract_json_ld_fallback(self, soup) -> Dict:
        try:
            for script in soup.find_all('script', type='application/ld+json'):
                try:
                    data = json.loads(script.string)
                    if isinstance(data, list): data = data[0] if data else {}
                    if data.get('@type') == 'Product':
                        return {
                            'brand': data.get('brand', {}).get('name'), 'category': data.get('category'),
                            'rating': data.get('aggregateRating', {}).get('ratingValue'),
                            'availability': data.get('offers', {}).get('availability', '').split('/')[-1]
                        }
                except: continue
        except: pass
        return {}

class EnhancedProductScraperWithGemini:
    """COMPLETE Gemini-enhanced product scraper with robust validation and video mapping."""

    def __init__(self, polite_delay=1, output_dir="gemini_scrape_output",
                 gemini_api_key=None, gemini_model="gemini-1.5-pro"):
        self.polite_delay = polite_delay
        self.output_dir = output_dir
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })
        self.setup_logging()
        os.makedirs(output_dir, exist_ok=True)
        self.urls_csv = os.path.join(output_dir, "product_urls.csv")
        self.html_dir = os.path.join(output_dir, "html_files")
        self.final_csv = os.path.join(output_dir, "final_products_gemini.csv")
        self.url_mapping_csv = os.path.join(output_dir, "url_mapping.csv")
        self.failures = {'url_extraction': [], 'html_fetching': [], 'detail_extraction': [], 'image_extraction': []}
        try:
            self.gemini_extractor = GeminiProductExtractor(api_key=gemini_api_key, model_name=gemini_model)
            self.logger.info(f"✅ Gemini extractor initialized with model: {self.gemini_extractor.model_name}")
        except Exception as e:
            self.logger.error(f"❌ Gemini initialization failed: {e}")
            raise

    def setup_logging(self):
        log_dir = os.path.join(self.output_dir, "logs")
        os.makedirs(log_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.logger = logging.getLogger('GeminiProductScraper')
        self.logger.setLevel(logging.INFO)
        if self.logger.hasHandlers(): self.logger.handlers.clear()
        file_handler = logging.FileHandler(os.path.join(log_dir, f'gemini_scraper_{timestamp}.log'), encoding='utf-8')
        console_handler = logging.StreamHandler()
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)
        self.logger.info(f"🚀 Gemini-Enhanced Scraper initialized. Output: {self.output_dir}")

    def log_failure(self, step, url, error, details=None):
        failure_record = {'timestamp': datetime.now().isoformat(), 'step': step, 'url': url, 'error': str(error), 'details': details or {}}
        self.failures[step].append(failure_record)
        self.logger.error(f"❌ FAILURE in {step}: {url} - {str(error).splitlines()[0]}")

    def _is_product_image(self, src: str) -> bool:
        if not src: return False
        skip_patterns = ['icon', 'logo', 'avatar', 'thumb', 'small', 'mini', 'badge', 'banner', 'header', 'footer', 'nav', '.svg', 'data:image', 'placeholder', 'payment', 'shipping']
        src_lower = src.lower()
        if any(pattern in src_lower for pattern in skip_patterns): return False
        product_patterns = ['product', 'item', 'gallery', 'main', 'large', 'zoom', 'variant']
        if any(pattern in src_lower for pattern in product_patterns): return True
        return True

    def detect_pagination_type(self, page, url):
        """Detects the pagination method used on the page."""
        if page.query_selector('a.next.page-numbers, a[aria-label="Next"], .pagination__next, [rel="next"]'):
            return "Next Button"
        if len(page.query_selector_all('.pagination .page-numbers')) > 1:
            return "Numbered"
        if page.query_selector('button:has-text("Load More"), .load-more-btn, a[rel="next"]'):
            return "Load More Button"
        if page.evaluate("document.body.scrollHeight > window.innerHeight * 2 and document.querySelector('.infinite-scroll')"):
            return "Infinite Scroll"
        if page.query_selector('.pagination'):
            return "Custom Pagination"
        return "Unknown (No Pagination Detected)"

    def parse_total_from_text(self, page):
        """Parses the total number of products from page text."""
        text = page.inner_text('body').lower()
        match = re.search(r'showing\s*\d+[-–]\d+\s*of\s*(\d+)', text)
        if match: return int(match.group(1))
        match = re.search(r'(\d+)\s*(items?|results?|products?)', text)
        if match: return int(match.group(1))
        match = re.search(r'(\d+)\s*total', text)
        if match: return int(match.group(1))
        return None

    def count_products_on_page(self, page, url):
        """Counts product links on the current page."""
        selectors = [
            'a[href*="/products/"]:not([href*="/collections/"]):not([href*="cart"]):not([href*="/pages/"])',
            'li.product a[href*="/product"], li.product a[href*="/products/"]',
            '.product-card a[href*="/product"], .product-card a[href*="/products/"]',
            '.grid-item a[href*="/item"], .grid-item a[href*="/products/"]',
            'a[href*="/product/"], a[href*="/products/"]'
        ]
        all_links = set()
        for sel in selectors:
            try:
                elems = page.query_selector_all(sel)
                for elem in elems:
                    try:
                        href = elem.get_attribute('href') or ''
                        if href and ('/products/' in href or '/product/' in href):
                            text = elem.inner_text().strip()
                            if len(text) > 5:
                                full_url = urljoin(url, href)
                                all_links.add(full_url)
                    except Exception:
                        continue
            except Exception:
                continue
        return len(all_links), all_links

    def get_all_products_and_pages(self, page, url, pagination_type, max_pages=50):
        """Traverses pagination and collects all product URLs."""
        exact_total = self.parse_total_from_text(page)
        all_product_urls = set()
        pages = 1
        count, page_urls = self.count_products_on_page(page, url)
        all_product_urls.update(page_urls)
        self.logger.info(f"  Page {pages}: Found {count} products")

        if exact_total:
            per_page = count if count > 0 else 1
            estimated_pages = (exact_total + per_page - 1) // per_page
            self.logger.info(f"  Found exact total from text: {exact_total}. Estimated pages: {estimated_pages}")
            if pagination_type in ["Next Button", "Numbered"]:
                while pages < min(max_pages, estimated_pages + 1):
                    try:
                        next_link = page.query_selector('a.next.page-numbers, a[aria-label="Next"], [rel="next"]')
                        if not next_link: break
                        href = next_link.get_attribute('href') or ''
                        if not href: break
                        next_url = urljoin(url, href)
                        if not next_url or next_url == url: break
                        page.goto(next_url, wait_until="domcontentloaded", timeout=30000)
                        page.wait_for_timeout(2000)
                        count, page_urls = self.count_products_on_page(page, next_url)
                        if count == 0 and len(page_urls) == 0: break
                        all_product_urls.update(page_urls)
                        pages += 1
                        self.logger.info(f"  Page {pages}: Found {len(page_urls)} new products")
                        url = next_url
                        time.sleep(self.polite_delay)
                    except Exception as e:
                        self.logger.warning(f"  Warning: Navigation error on page {pages+1}: {e}")
                        break
            return pages, exact_total, all_product_urls

        # Fallback for when no exact total is found
        if pagination_type in ["Next Button", "Numbered"]:
            while pages < max_pages:
                try:
                    next_link = page.query_selector('a.next.page-numbers, a[aria-label="Next"], [rel="next"]')
                    if not next_link: break
                    href = next_link.get_attribute('href') or ''
                    if not href: break
                    next_url = urljoin(url, href)
                    if not next_url or next_url == url: break
                    page.goto(next_url, wait_until="domcontentloaded", timeout=30000)
                    page.wait_for_timeout(2000)
                    count, page_urls = self.count_products_on_page(page, next_url)
                    new_links = page_urls - all_product_urls
                    if not new_links:
                        self.logger.info("  No new products found on the next page. Stopping.")
                        break
                    all_product_urls.update(new_links)
                    pages += 1
                    self.logger.info(f"  Page {pages}: Found {len(new_links)} new products")
                    url = next_url
                    time.sleep(self.polite_delay)
                except Exception as e:
                    self.logger.warning(f"  Warning: Navigation error on page {pages+1}: {e}")
                    break
            return pages, len(all_product_urls), all_product_urls

        elif pagination_type == "Load More Button":
            clicks, max_clicks = 0, 15
            while clicks < max_clicks:
                try:
                    btn = page.query_selector('button:has-text("Load More"), .load-more-btn')
                    if not btn or not btn.is_visible(): break
                    initial_count = len(all_product_urls)
                    btn.click()
                    page.wait_for_timeout(3000) # Wait for content to load
                    _, page_urls = self.count_products_on_page(page, url)
                    all_product_urls.update(page_urls)
                    if len(all_product_urls) == initial_count:
                        self.logger.info("  'Load More' did not add new products. Stopping.")
                        break
                    clicks += 1
                    self.logger.info(f"  'Load More' click {clicks}: Total products now {len(all_product_urls)}")
                except Exception:
                    break
            return clicks + 1, len(all_product_urls), all_product_urls

        elif pagination_type == "Infinite Scroll":
            scrolls, max_scrolls = 0, 15
            while scrolls < max_scrolls:
                try:
                    initial_count = len(all_product_urls)
                    page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    page.wait_for_timeout(4000) # Wait for content to load
                    _, page_urls = self.count_products_on_page(page, url)
                    all_product_urls.update(page_urls)
                    if len(all_product_urls) == initial_count:
                        self.logger.info("  Infinite scroll did not add new products. Stopping.")
                        break
                    scrolls += 1
                    self.logger.info(f"  Scroll {scrolls}: Total products now {len(all_product_urls)}")
                except Exception:
                    break
            return scrolls + 1, len(all_product_urls), all_product_urls

        # Default case for Unknown pagination
        self.logger.info("  Unknown pagination: Simulating one scroll just in case.")
        try:
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            page.wait_for_timeout(3000)
            _, page_urls = self.count_products_on_page(page, url)
            all_product_urls.update(page_urls)
        except Exception: pass
        return 1, len(all_product_urls), all_product_urls

    def extract_product_urls(self, category_task):
        """
        Uses Playwright to handle complex pagination and extract all product URLs from a category.
        """
        cat_id, url, brand = category_task['category_id'], category_task['url'], category_task['brand']
        self.logger.info(f"🚀 Starting Playwright URL extraction from: {url} (Category: {cat_id})")
        product_tasks = []
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True, args=['--no-sandbox', '--disable-blink-features=AutomationControlled'])
                context = browser.new_context(
                    user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    viewport={'width': 1920, 'height': 1080}
                )
                page = context.new_page()
                page.goto(url, wait_until="domcontentloaded", timeout=90000)
                page.wait_for_timeout(4000)
                pagination_type = self.detect_pagination_type(page, url)
                self.logger.info(f"  Detected Pagination Type: {pagination_type}")
                _, _, all_urls = self.get_all_products_and_pages(page, url, pagination_type)
                browser.close()

                for product_url in sorted(list(all_urls)):
                    product_tasks.append({
                        'url': product_url,
                        'category_id': cat_id,
                        'brand': brand
                    })
                self.logger.info(f"✅ Extracted {len(product_tasks)} product URLs for category {cat_id}")
        except Exception as e:
            self.log_failure('url_extraction', url, e, {'step': 'playwright_extract_product_urls'})
            self.logger.error(f"  Failed to extract URLs for {url} due to an error: {e}")
        return product_tasks

    def get_user_input(self):
        print("\n--- Enhanced Gemini Product Scraper ---")
        category_tasks = []
        print("\n--- Step 1: Provide Category Information via CSV File ---")
        print("The CSV file should have NO HEADER and columns: Category ID (e.g., 01_02_03), URL, Brand (optional)")
        while True:
            csv_path = input("\nEnter the full path to your input CSV file: ").strip().strip('"')
            if not os.path.isfile(csv_path):
                print(f"Error: The file '{csv_path}' was not found.")
                continue
            try:
                df = pd.read_csv(csv_path, header=None, on_bad_lines="warn").fillna("")
                if df.shape[1] < 2:
                    print("Error: The CSV file must have at least 2 columns.")
                    continue
                df.columns = ["category_id", "url", "brand"][:df.shape[1]]
                for index, row in df.iterrows():
                    category_id, url = str(row["category_id"]).strip(), str(row["url"]).strip()
                    row_brand = str(row.get("brand", "")).strip()
                    if not category_id or not url.startswith("http"):
                        print(f"Warning: Skipping row {index + 1} due to invalid data.")
                        continue
                    if not row_brand:
                        if not category_tasks:
                            print("Error: No brand provided in first row. Please add a brand column.")
                            continue
                        row_brand = category_tasks[0]['brand']  # Use first row's brand as fallback
                    category_tasks.append({
                        "category_id": category_id,
                        "url": url,
                        "brand": row_brand
                    })
                if not category_tasks:
                    print("Warning: No valid category tasks were created from the CSV.")
                    continue
                print(f"\nSuccessfully loaded {len(category_tasks)} categories with brand '{category_tasks[0]['brand']}'.")
                self.brand_id = category_tasks[0]['brand']  # Set global brand_id from first row
                break
            except Exception as e:
                print(f"An error occurred while reading the CSV file: {e}")
        if not category_tasks: return None, None
        while True:
            try:
                max_workers = int(input("\n--- Step 2: Enter number of concurrent threads (e.g., 5-10): "))
                if max_workers > 0: break
                else: print("Please enter a positive number.")
            except ValueError: print("Invalid input. Please enter a number.")
        return category_tasks, max_workers

    def generate_filename_from_url(self, url):
        parsed_url = urlparse(url)
        path_component = parsed_url.path.replace('/', '_').replace('\\', '_')
        filename = f"{parsed_url.netloc}{path_component}.html"
        return "".join(c for c in filename if c.isalnum() or c in ('_', '.', '-')).rstrip('._-')

    # ===================================================================
    # ## START: FINAL ROBUST SOLUTION
    # ===================================================================

    def fetch_all_html_files(self, product_tasks, max_workers):
        self.logger.info(f"🔄 Starting HTML fetching for {len(product_tasks)} URLs using isolated workers...")
        os.makedirs(self.html_dir, exist_ok=True)
        url_mapping = []

        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Each task is submitted to the worker, which will handle its own Playwright instance.
            futures = [executor.submit(self.fetch_page_content_worker, task) for task in product_tasks]

            for future in concurrent.futures.as_completed(futures):
                result = future.result()
                if result:
                    url_mapping.append(result)

        self.logger.info(f"✅ Fetched {len(url_mapping)}/{len(product_tasks)} HTML files.")
        if url_mapping:
            with open(self.url_mapping_csv, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=['original_url', 'filename', 'filepath', 'category_id', 'brand'])
                writer.writeheader()
                writer.writerows(url_mapping)

        return [m for m in url_mapping if m]

    def fetch_page_content_worker(self, task):
        """
        A thread-safe worker that creates its own Playwright instance for each task.
        This is the most robust way to prevent threading errors.
        """
        url = task['url']
        filename = self.generate_filename_from_url(url)
        output_file_path = os.path.join(self.html_dir, filename)

        try:
            with sync_playwright() as p:
                browser = p.chromium.launch()
                page = browser.new_page()
                try:
                    self.logger.info(f"🌐 [{threading.get_ident()}] Fetching: {url}")
                    page.goto(url, wait_until="networkidle", timeout=60000)
                    time.sleep(2) # Wait for dynamic content

                    with open(output_file_path, "w", encoding="utf-8") as f:
                        f.write(page.content())

                    self.logger.info(f"✅ Success! Saved '{os.path.basename(output_file_path)}'")
                    return {
                        'original_url': url,
                        'filename': filename,
                        'filepath': output_file_path,
                        'category_id': task['category_id'],
                        'brand': task['brand']
                    }
                finally:
                    page.close()
                    browser.close()
        except Exception as e:
            self.log_failure('html_fetching', url, e, {'output_path': output_file_path})
            return None

    # ===================================================================
    # ## END: FINAL ROBUST SOLUTION
    # ===================================================================

    def process_html_files_to_csv_with_gemini(self, url_mappings, max_workers):
        self.logger.info(f"🤖 Starting enhanced product extraction from {len(url_mappings)} mappings")
        base_folder = f"{self.brand_id}_gemini_scrape_{time.strftime('%Y%m%d-%H%M%S')}"
        base_folder_path = os.path.join(self.output_dir, base_folder)
        os.makedirs(base_folder_path, exist_ok=True)
        self.logger.info(f"📁 Output folder: {base_folder_path}")
        results = []
        try:
            worker_func = partial(self.process_single_html_worker, base_folder_path)
            with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = [executor.submit(worker_func, mapping) for mapping in url_mappings]
                for future in concurrent.futures.as_completed(futures):
                    result = future.result()
                    if result:
                        results.append(result)
                    time.sleep(self.polite_delay)
            if results: self.save_results_to_csv(results, base_folder_path)
            self.logger.info(f"🎯 EXTRACTION COMPLETE: {len(results)} successful")
            return len(results) > 0
        except Exception as e:
            self.log_failure('detail_extraction', 'general', e)
            return False

    def process_single_html_worker(self, base_folder_path, mapping):
        file_path = mapping['filepath']
        original_url = mapping['original_url']
        category_id = mapping['category_id']
        brand = mapping['brand']
        filename = os.path.basename(file_path)
        self.logger.info(f"🔍 Processing: {filename}")
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f: html_content = f.read()
            if not html_content.strip(): return None
            product_data = self.gemini_extractor.extract_product_details(html_content, original_url)
            if product_data.title and product_data.title not in ["Unknown Product", "Extraction Failed", "Product Title Not Found"]:
                pass  # Success
            product_record = self.convert_to_csv_format(product_data, original_url, base_folder_path, category_id, brand)
            self.logger.info(f"✅ Success: {product_data.title[:60]}...")
            return product_record
        except Exception as e:
            self.log_failure('detail_extraction', file_path, e)
            return None

    def _find_dynamic_attribute(self, keyword: str, all_attrs: dict) -> str:
        """
        Dynamically searches for a keyword in attribute keys.
        This is more flexible than a fixed list of aliases.
        """
        pattern = re.compile(rf'\b{re.escape(keyword)}\b', re.IGNORECASE)
        for key, value in all_attrs.items():
            if pattern.search(key):
                return str(value) # Return the value of the first matching key
        return ""

    def _validate_with_aliases(self, attr_name: str, all_attrs: dict) -> str:
        for alias in ATTRIBUTE_ALIASES.get(attr_name, []):
            extracted_value = all_attrs.get(alias.lower())

            # Check if we actually found a non-empty value for this alias
            if extracted_value and isinstance(extracted_value, str):
                valid_matches = []
                validation_set_key = attr_name + 's'
                master_list_for_validation = VALIDATION_SETS.get(validation_set_key, set())

                delimiters = re.compile(r'[,/|&]|\s+and\s+', re.IGNORECASE)
                potential_values = delimiters.split(extracted_value)

                for value in potential_values:
                    clean_value = value.strip()
                    if clean_value and clean_value.lower() in master_list_for_validation:
                        for master_val in MASTER_VALUES.get(validation_set_key, []):
                            if master_val.lower() == clean_value.lower():
                                valid_matches.append(master_val)
                                break

                # If we found at least one valid match among the potential values
                if valid_matches:
                    return ", ".join(sorted(list(set(valid_matches))))

                else:
                    self.logger.warning(
                        f"Validation failed for '{attr_name}'. Value '{extracted_value}' not in master list. Using placeholder."
                    )
                    return f"Test {attr_name.title()}"

        # If the loop finishes without finding any key that matches an alias, return empty.
        return ""

    def convert_to_csv_format(self, product_data: ProductSchema, original_url: str, base_folder_path: str, category_id: str, brand: str) -> Dict:
        """MODIFIED: Integrates new dynamic 'finish' search and alias-based validation."""

        def sanitize_price(price_str):
            if not price_str:
                return ""
            match = re.search(r"(\d[\d,]*)", price_str)
            if match:
                return match.group(1).replace(",", "")
            return ""

        product_id = f"bw_{brand}_{uuid.uuid4().hex[:6]}"
        product_name = f"{brand.title()} {product_data.title.title()} {product_id.split('_')[-1]}"

        # Map categories using split/pad logic
        cat_parts = category_id.split("_")
        category_level1 = cat_parts[0].zfill(2) if cat_parts else "N/A"
        category_level2 = f"{cat_parts[0].zfill(2)}_{cat_parts[1].zfill(2)}" if len(cat_parts) >= 2 else "N/A"
        category_level3 = "_".join([p.zfill(2) for p in cat_parts]) if cat_parts else "N/A"

        other_information_parts = []
        if product_data.specifications:
            for k, v in product_data.specifications.items():
                if k and v:
                    other_information_parts.append(f"{k}: {v}")
        if product_data.features:
            other_information_parts.extend(product_data.features)
        if product_data.sku:
            other_information_parts.append(f"SKU: {product_data.sku}")
        other_information = " | ".join(other_information_parts)
        clean_description = product_data.description or "Not found"

        all_attrs = {}
        if product_data.specifications:
            all_attrs.update({k.lower(): v for k, v in product_data.specifications.items()})

        # --- MODIFIED: Using a mix of validation strategies ---
        validated_color = self._validate_with_aliases('color', all_attrs)
        validated_material = self._validate_with_aliases('material', all_attrs)
        validated_shape = self._validate_with_aliases('shape', all_attrs)
        validated_type = self._validate_with_aliases('type', all_attrs)

        # Use the NEW dynamic search for 'finish'
        validated_finish = self._find_dynamic_attribute('finish', all_attrs)
        # --- End of validation logic ---

        youtube_link = product_data.youtube_url or ""
        other_videos = "|".join(product_data.video_urls) if product_data.video_urls else ""

        product_price =sanitize_price(product_data.price)  # price

        self.logger.info(f"🚀 Starting live image fetch for {product_data.title[:30]}...")
        image_folder_path = os.path.join(base_folder_path, product_id)
        saved_image_names = self.fetch_and_download_images_from_live_url(
            product_url=original_url, image_folder_path=image_folder_path, product_id=product_id
        )
        self.logger.info(f"✅ Saved {len(saved_image_names)} images from the live URL.")

        return {
            "brand_id": brand, "productrange_simple": "1", "product_name": product_name,
            "product_id": product_id, "category_level1": category_level1, "category_level2": category_level2,
            "category_level3": category_level3, "price_choice": "", "min_price": product_price or "", "price_unit": "",
            "original_price": product_data.original_price or "",
            "description": clean_description,
            "product_images": "|".join(saved_image_names),
            "video": other_videos,
            "brouchure_pdf": "",
            "youtube": youtube_link,
            "other_information": other_information,
            "color": validated_color,
            "shape": validated_shape,
            "material": validated_material,
            "application": "",
            "finish": validated_finish, # MODIFIED
            "type": validated_type,
            "grade": self._find_dynamic_attribute('grade', all_attrs), # Also using dynamic search for grade
            "service_category": "", "Remarks": f"Enhanced extraction with {self.gemini_extractor.model_name}",
            "bw_rating": str(product_data.rating) if product_data.rating else "", "meta_keywords": "",
            "online_links": "", "product_url": original_url, "sku": product_data.sku or "",
            "availability": product_data.availability or "", "review_count": str(product_data.review_count) if product_data.review_count else "",
            "shipping_info": product_data.shipping_info or "", "return_policy": product_data.return_policy or ""
        }

    def fetch_and_download_images_from_live_url(self, product_url: str, image_folder_path: str, product_id: str) -> List[str]:
        if not product_url:
            self.logger.warning("Skipping live image fetch: No product URL provided.")
            return []
        self.logger.info(f"📸 Starting intelligent image search on live URL: {product_url}")
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch()
                page = browser.new_page()
                page.goto(product_url, wait_until="load", timeout=90000)
                page.wait_for_timeout(3000)
                gallery_selectors = [
                    '[class*="product-gallery"]', '[class*="product--media"]', '[class*="product__media-gallery"]',
                    '[class*="product-images"]', '[class*="product-image-gallery"]', '[class*="product__image"]',
                    '[data-testid*="gallery"]', '.product-gallery', '.product-images', '.product-main-image'
                ]
                image_container = None
                for selector in gallery_selectors:
                    container_candidate = page.locator(selector).first
                    if container_candidate.count() > 0:
                        is_related = container_candidate.locator('xpath=ancestor::*[contains(@class, "related") or contains(@class, "recommend")]').count() > 0
                        if not is_related:
                            self.logger.info(f"✅ Found main image container with selector: '{selector}'")
                            image_container = container_candidate
                            break
                if image_container:
                    image_elements = image_container.locator('img').all()
                    self.logger.info(f"Found {len(image_elements)} images within the main product container.")
                else:
                    self.logger.warning("Could not find a dedicated product image container. Searching <main> tag.")
                    image_elements = page.locator('main img').all()
                image_urls = set()
                for img_element in image_elements:
                    src = img_element.get_attribute('src')
                    if not src or src.startswith('data:image') or '.svg' in src: continue
                    try:
                        box = img_element.bounding_box()
                        if box and (box['width'] < 300 or box['height'] < 300):
                            continue
                    except Exception: pass
                    full_url = urljoin(product_url, src)
                    if self._is_product_image(full_url): image_urls.add(full_url)
                browser.close()
            self.logger.info(f"Found {len(image_urls)} high-quality product image URLs after filtering.")
            saved_image_names = []
            for idx, image_url in enumerate(list(image_urls)[:10]):
                file_name = f"{product_id}_{idx + 1}"
                saved_name = self.download_image(image_url, image_folder_path, file_name)
                if saved_name: saved_image_names.append(saved_name)
            return saved_image_names
        except Exception as e:
            self.log_failure('image_extraction', product_url, e, {'step': 'fetch_live_images_intelligent'})
            return []

    def download_image(self, image_url, folder_path, image_name):
        if not image_url or not image_url.startswith(("http://", "https://")): return None
        try:
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36', 'Accept': 'image/*,*/*;q=0.8'}
            response = self.session.get(image_url, timeout=20, headers=headers)
            response.raise_for_status()
            if not response.headers.get('content-type', '').lower().startswith('image/'): return None
            img = Image.open(io.BytesIO(response.content))
            if img.size[0] < 640 or img.size[1] < 640: img = img.resize((650, 650), Image.Resampling.LANCZOS)
            if img.mode != "RGB": img = img.convert("RGB")
            filename = f"{re.sub(r'[\\/*?:\"<>|]', '', image_name)}.jpg"
            os.makedirs(folder_path, exist_ok=True)
            filepath = os.path.join(folder_path, filename)
            img.save(filepath, "JPEG", quality=95)
            return filename
        except Exception as e:
            self.log_failure('image_extraction', image_url, e)
            return None

    def save_results_to_csv(self, results, base_folder_path):
        if not results: return
        df = pd.DataFrame(results)
        desired_columns = [
            "brand_id", "productrange_simple", "product_name", "product_id", "category_level1", "category_level2", "category_level3",
            "price_choice", "min_price", "original_price", "price_unit", "description", "product_images", "video", "brouchure_pdf", "youtube",
            "other_information", "color", "shape", "material", "application", "finish", "type", "grade", "service_category", "Remarks",
            "bw_rating", "review_count", "sku", "availability", "shipping_info", "return_policy", "meta_keywords", "online_links", "product_url"
        ]
        for col in desired_columns:
            if col not in df.columns: df[col] = ""
        df = df[desired_columns]
        output_filename = os.path.join(base_folder_path, "final_products_gemini.csv")
        df.to_csv(output_filename, index=False, encoding="utf-8-sig")
        self.logger.info(f"💾 Saved final CSV: {output_filename}")
        total = len(df)
        desc_count = sum(1 for d in df['description'] if d and d != "Not found")
        price_count = sum(1 for p in df['min_price'] if p)
        img_count = sum(1 for i in df['product_images'] if i)
        self.logger.info(f"📊 CSV Stats: Descriptions({desc_count}/{total}), Prices({price_count}/{total}), Images({img_count}/{total})")

    def save_failure_report(self):
        failure_file = os.path.join(self.output_dir, "failure_report.json")
        summary = {'total_failures': sum(len(f) for f in self.failures.values()), 'failures_by_step': {s: len(f) for s, f in self.failures.items()}}
        report = {'summary': summary, 'detailed_failures': self.failures}
        with open(failure_file, 'w', encoding='utf-8') as f: json.dump(report, f, indent=2, ensure_ascii=False)
        self.logger.info(f"📊 Failure report saved: {failure_file}")

    def _robust_delete(self, path_to_delete):
        """Robustly deletes a file or directory with retries."""
        max_retries = 3
        retry_delay = 2  # seconds

        for attempt in range(max_retries):
            try:
                if os.path.exists(path_to_delete):
                    if os.path.isdir(path_to_delete):
                        shutil.rmtree(path_to_delete)
                        self.logger.info(f"✅ Successfully deleted temporary directory: {path_to_delete}")
                    else:
                        os.remove(path_to_delete)
                        self.logger.info(f"✅ Successfully deleted temporary file: {path_to_delete}")
                    return  # Exit the function on success
                else:
                    self.logger.info(f"✅ Path not found, no action needed: {path_to_delete}")
                    return  # Exit as there's nothing to do
            except OSError as e:
                self.logger.warning(f"⚠️ Attempt {attempt + 1}/{max_retries} failed to delete '{path_to_delete}'. Error: {e}")
                if attempt < max_retries - 1:
                    self.logger.info(f"Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                else:
                    self.logger.error(f"❌ Failed to delete '{path_to_delete}' after {max_retries} attempts. Please delete it manually.")

    def run_complete_pipeline_with_gemini(self, category_tasks, max_workers):
        self.logger.info("🚀 Starting COMPLETE Enhanced Gemini Pipeline")
        self.logger.info("="*80 + "\n📍 STEP 1: Extracting Product URLs (Upgraded with Playwright)\n" + "="*80)
        all_product_tasks = []
        seen_urls = set()
        for i, task in enumerate(category_tasks, 1):
            self.logger.info(f"📍 Processing Category {i}/{len(category_tasks)}: {task['url']} (ID: {task['category_id']}, Brand: {task['brand']})")
            try:
                category_products = self.extract_product_urls(task)
                for p_task in category_products:
                    if p_task['url'] not in seen_urls:
                        all_product_tasks.append(p_task)
                        seen_urls.add(p_task['url'])
                if i < len(category_tasks): time.sleep(self.polite_delay * 2)
            except Exception as e:
                self.log_failure('url_extraction', task['url'], e)
        if all_product_tasks:
            with open(self.urls_csv, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=['url', 'category_id', 'brand'])
                writer.writeheader()
                writer.writerows(all_product_tasks)
            self.logger.info(f"✅ Total unique product tasks collected: {len(all_product_tasks)}")
        else:
            self.logger.error("❌ No product tasks collected. Pipeline stopped.")
            self.save_failure_report(); return False

        self.logger.info("\n" + "="*80 + "\n📥 STEP 2: Fetching HTML Files\n" + "="*80)
        url_mappings = self.fetch_all_html_files(all_product_tasks, max_workers)
        if not url_mappings:
            self.logger.error("❌ HTML fetching failed."); self.save_failure_report(); return False

        self.logger.info("\n" + "="*80 + "\n🤖 STEP 3: Enhanced Product Detail Extraction\n" + "="*80)
        if not self.process_html_files_to_csv_with_gemini(url_mappings, max_workers):
            self.logger.error("❌ Product extraction failed."); self.save_failure_report(); return False

        self.logger.info("\n" + "="*80 + "\n🧹 STEP 4: Cleaning up temporary files\n" + "="*80)

        # List of temporary files and directories to clean up
        temp_paths_to_delete = [
            self.html_dir,
            self.urls_csv,
            self.url_mapping_csv
        ]

        for path in temp_paths_to_delete:
            self._robust_delete(path)

        self.logger.info("\n" + "="*80 + "\n🎉 ENHANCED PIPELINE COMPLETE!\n" + "="*80)
        self.save_failure_report()
        return True

# Usage example
def main():
    """Complete enhanced scraper example"""
    import time

    output_directory = f"scrape_output_{time.strftime('%Y%m%d-%H%M%S')}"

    GEMINI_API_KEY = os.getenv("GOOGLE_AI_API_KEY")

    if not GEMINI_API_KEY:
        print("❌ GOOGLE_AI_API_KEY not found. Please set it as an environment variable.")
        return

    scraper = EnhancedProductScraperWithGemini(
        polite_delay=1,
        output_dir=output_directory,
        gemini_api_key=GEMINI_API_KEY,
        gemini_model="gemini-1.5-pro"
    )

    print("🚀 Starting COMPLETE enhanced scraping pipeline...")
    print(f"🤖 Using model: {scraper.gemini_extractor.model_name}")
    print(f"📁 Output directory: {scraper.output_dir}")

    category_tasks, max_workers = scraper.get_user_input()
    if not category_tasks or not max_workers:
        print("❌ Invalid input. Exiting.")
        return

    success = scraper.run_complete_pipeline_with_gemini(category_tasks, max_workers)

    if success:
        print("\n✅ COMPLETE enhanced pipeline executed successfully!")
        print("📊 Check the output directory for results.")
    else:
        print("\n❌ Pipeline failed. Check logs for details.")

if __name__ == "__main__":
    main()
